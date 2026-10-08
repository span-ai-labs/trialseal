"""Outside time-stamping services, which supply the anchors that show a seal existed on a date.

Two independent kinds are used so that the proof does not rest on one party: a
signed reply from an RFC 3161 time-stamping authority, and an OpenTimestamps
proof that is later completed in the Bitcoin block chain.

An RFC 3161 anchor is verified here with OpenSSL: signature, certificate chain,
fingerprint and signing time. An OpenTimestamps anchor is only checked for its
layout and for the fingerprint it is about; whether it has reached the block
chain is confirmed with the official client (`ots verify`). Both anchors are
stored as the files those standard tools read.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import shutil
import ssl
import subprocess
import tempfile
import urllib.request
from typing import Callable, NamedTuple, Protocol

Post = Callable[[str, bytes, dict[str, str]], bytes]

METHODS = ("rfc3161", "opentimestamps")


class AnchorFailed(Exception):
    """A time-stamping service's reply is not a valid anchor for the fingerprint."""


class AnchorCheck(NamedTuple):
    signed_on: dt.date | None  # the day the service signed, where the anchor states one
    complete: bool  # False while an OpenTimestamps anchor still waits to enter the block chain


def http_post(url: str, data: bytes, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, data=data, headers={"User-Agent": "trialseal", **headers}, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


class TimestampService(Protocol):
    method: str

    def anchor(self, fingerprint: str) -> bytes: ...

    def verify(self, fingerprint: str, anchor: bytes) -> AnchorCheck: ...


# A SHA-256 time-stamp request with no nonce, asking for the signing certificate: the fixed
# DER around the 32-byte digest. Byte-identical to `openssl ts -query -sha256 -cert -no_nonce`.
_RFC3161_BEFORE_DIGEST = bytes.fromhex("30390201013031300d060960864801650304020105000420")
_RFC3161_AFTER_DIGEST = bytes.fromhex("0101ff")


class Rfc3161Service:
    """An RFC 3161 time-stamping authority. Its anchors are verified with OpenSSL."""

    method = "rfc3161"

    def __init__(self, url: str, post: Post = http_post, ca_file: str | None = None, openssl: str | None = None) -> None:
        self._url, self._post = url, post
        self._ca_file = ca_file or ssl.get_default_verify_paths().cafile or "/etc/ssl/cert.pem"
        self._openssl = openssl or shutil.which("openssl")

    def anchor(self, fingerprint: str) -> bytes:
        request = _RFC3161_BEFORE_DIGEST + bytes.fromhex(fingerprint) + _RFC3161_AFTER_DIGEST
        reply = self._post(self._url, request, {"Content-Type": "application/timestamp-query"})
        self.verify(fingerprint, reply)
        return reply

    def verify(self, fingerprint: str, anchor: bytes) -> AnchorCheck:
        """Check signature, certificate chain and fingerprint with OpenSSL, and read the signed day."""
        if self._openssl is None:
            raise AnchorFailed("OpenSSL is needed to verify an RFC 3161 anchor")

        def openssl(*arguments: str) -> subprocess.CompletedProcess:
            return subprocess.run([self._openssl, *arguments], capture_output=True, text=True)

        with tempfile.TemporaryDirectory() as held:
            reply, token, certificates = (f"{held}/{name}" for name in ("reply.tsr", "token.p7", "certificates.pem"))
            pathlib.Path(reply).write_bytes(anchor)
            # The authority's own certificates travel inside the token. Older OpenSSL builds only
            # follow the chain if they are handed over separately.
            openssl("ts", "-reply", "-in", reply, "-token_out", "-out", token)
            openssl("pkcs7", "-inform", "DER", "-in", token, "-print_certs", "-out", certificates)
            verified = openssl("ts", "-verify", "-digest", fingerprint, "-in", reply, "-CAfile", self._ca_file,
                               "-untrusted", certificates)
            if verified.returncode != 0 or "Verification: OK" not in verified.stdout:
                raise AnchorFailed(f"OpenSSL did not verify the RFC 3161 anchor for {fingerprint}")
            # Described from the token alone: the reply's status text is not signed and could say anything.
            described = openssl("ts", "-reply", "-in", reply, "-token_out", "-text").stdout
        for line in described.splitlines():
            if line.startswith("Time stamp:"):
                signed_at = dt.datetime.strptime(line.removeprefix("Time stamp:").strip(), "%b %d %H:%M:%S %Y GMT")
                return AnchorCheck(signed_on=signed_at.date(), complete=True)
        raise AnchorFailed("the RFC 3161 anchor states no signing time")


# The start of an OpenTimestamps proof file for a SHA-256 digest: magic, version 1, SHA-256 tag.
_OTS_HEADER = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01\x08"
_OTS_AWAITING_BLOCK_CHAIN = bytes.fromhex("83dfe30d2ef90c8e")
_OTS_IN_BLOCK_CHAIN = bytes.fromhex("0588960d73d71901")


class OpenTimestampsService:
    """An OpenTimestamps calendar server. Its anchors are proof files the official client reads."""

    method = "opentimestamps"

    def __init__(self, calendar_url: str, post: Post = http_post) -> None:
        self._url, self._post = calendar_url.rstrip("/") + "/digest", post

    def anchor(self, fingerprint: str) -> bytes:
        digest = bytes.fromhex(fingerprint)
        reply = self._post(self._url, digest, {
            "Accept": "application/vnd.opentimestamps.v1", "Content-Type": "application/x-www-form-urlencoded"})
        proof = _OTS_HEADER + digest + reply
        self.verify(fingerprint, proof)
        return proof

    def verify(self, fingerprint: str, anchor: bytes) -> AnchorCheck:
        """Check the proof file's layout and fingerprint. It does not check the block chain; `ots verify` does."""
        start = _OTS_HEADER + bytes.fromhex(fingerprint)
        attested = anchor[len(start):]
        if not anchor.startswith(start) or not (_OTS_AWAITING_BLOCK_CHAIN in attested or _OTS_IN_BLOCK_CHAIN in attested):
            raise AnchorFailed(f"not an OpenTimestamps anchor for {fingerprint}")
        return AnchorCheck(signed_on=None, complete=_OTS_IN_BLOCK_CHAIN in attested)


def configured_services(chosen: pathlib.Path) -> list[TimestampService]:
    """One service of each kind, at the addresses the setup wizard recorded."""
    addresses = json.loads(chosen.read_text(encoding="utf-8"))
    missing = [method for method in METHODS if not addresses.get(method)]
    if missing:
        raise ValueError(f"{chosen} names no service for: {', '.join(missing)}")
    return [Rfc3161Service(addresses["rfc3161"]), OpenTimestampsService(addresses["opentimestamps"])]
