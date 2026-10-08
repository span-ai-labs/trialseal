"""Time-stamping services, tested against replies recorded from the real services on 2026-10-08."""
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil

import pytest

from trialforecast.anchors import AnchorFailed, OpenTimestampsService, Rfc3161Service, configured_services

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
FINGERPRINT = hashlib.sha256(b"trialseal test fixture").hexdigest()
OTHER_FINGERPRINT = hashlib.sha256(b"something else").hexdigest()
DIGICERT = (FIXTURES / "rfc3161_digicert.tsr").read_bytes()
CALENDAR_REPLY = (FIXTURES / "opentimestamps_alice.response").read_bytes()
OTS_HEADER = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01\x08"

needs_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="OpenSSL verifies RFC 3161 anchors")


def replying(response, sent=None):
    def post(url, data, headers):
        if sent is not None:
            sent.append((url, data, headers))
        return response
    return post


@needs_openssl
def test_rfc3161_service_sends_the_fingerprint_and_keeps_the_signed_reply():
    sent = []
    service = Rfc3161Service("https://tsa.example/tsr", post=replying(DIGICERT, sent))

    assert service.anchor(FINGERPRINT) == DIGICERT
    (url, request, headers), = sent
    assert url == "https://tsa.example/tsr"
    assert request == (FIXTURES / "rfc3161_request.tsq").read_bytes()  # byte-identical to OpenSSL's own request
    assert headers["Content-Type"] == "application/timestamp-query"


@needs_openssl
def test_rfc3161_anchor_is_checked_by_openssl_for_signature_fingerprint_and_date():
    service = Rfc3161Service("https://tsa.example/tsr")
    check = service.verify(FINGERPRINT, DIGICERT)
    assert (check.signed_on, check.complete) == (dt.date(2026, 10, 8), True)

    forged = bytes.fromhex("30053003020100") + bytes.fromhex(FINGERPRINT)       # "granted", then the digest
    appended = DIGICERT + bytes.fromhex(OTHER_FINGERPRINT)                      # a real anchor for something else
    for fingerprint, anchor in ((OTHER_FINGERPRINT, DIGICERT), (FINGERPRINT, forged), (OTHER_FINGERPRINT, appended),
                                (FINGERPRINT, b"not an anchor"), (FINGERPRINT, b"")):
        with pytest.raises(AnchorFailed):
            service.verify(fingerprint, anchor)


@needs_openssl
def test_rfc3161_service_refuses_a_reply_that_is_not_an_anchor_for_what_it_sent():
    rejected = bytes.fromhex("30053003020102")  # status 2: rejection
    with pytest.raises(AnchorFailed):
        Rfc3161Service("https://tsa.example/tsr", post=replying(rejected)).anchor(FINGERPRINT)
    with pytest.raises(AnchorFailed):
        Rfc3161Service("https://tsa.example/tsr", post=replying(DIGICERT)).anchor(OTHER_FINGERPRINT)


def test_opentimestamps_service_builds_a_proof_file_the_official_client_reads():
    sent = []
    service = OpenTimestampsService("https://calendar.example/", post=replying(CALENDAR_REPLY, sent))

    anchor = service.anchor(FINGERPRINT)
    (url, submitted, _), = sent
    assert url == "https://calendar.example/digest"
    assert submitted == bytes.fromhex(FINGERPRINT)
    # Magic, version 1, SHA-256 tag, the digest, then the calendar's reply: checked with `ots info` on 2026-10-08.
    assert anchor == OTS_HEADER + bytes.fromhex(FINGERPRINT) + CALENDAR_REPLY

    check = service.verify(FINGERPRINT, anchor)
    assert (check.signed_on, check.complete) == (None, False)  # waiting to be written into the block chain


def test_opentimestamps_anchor_must_be_for_the_fingerprint_and_carry_an_attestation():
    service = OpenTimestampsService("https://calendar.example")
    good = OTS_HEADER + bytes.fromhex(FINGERPRINT) + CALENDAR_REPLY
    for fingerprint, anchor in ((OTHER_FINGERPRINT, good),
                                (FINGERPRINT, OTS_HEADER + bytes.fromhex(FINGERPRINT)),             # nothing after it
                                (FINGERPRINT, OTS_HEADER + bytes.fromhex(FINGERPRINT) + b"\x00"),   # no attestation
                                (FINGERPRINT, b"")):
        with pytest.raises(AnchorFailed):
            service.verify(fingerprint, anchor)
    with pytest.raises(AnchorFailed):
        OpenTimestampsService("https://calendar.example", post=replying(b"")).anchor(FINGERPRINT)


def test_the_services_recorded_by_the_setup_wizard_are_one_of_each_kind(tmp_path):
    chosen = tmp_path / "anchors.json"
    chosen.write_text(json.dumps({"rfc3161": "http://timestamp.digicert.com",
                                  "opentimestamps": "https://alice.btc.calendar.opentimestamps.org"}))
    services = configured_services(chosen)
    assert [type(s) for s in services] == [Rfc3161Service, OpenTimestampsService]
    assert [s.method for s in services] == ["rfc3161", "opentimestamps"]
    chosen.write_text(json.dumps({"rfc3161": "http://timestamp.digicert.com"}))
    with pytest.raises(ValueError, match="opentimestamps"):
        configured_services(chosen)


@pytest.mark.skipif(os.environ.get("TRIALSEAL_LIVE") != "1", reason="set TRIALSEAL_LIVE=1 to call the real services")
def test_the_real_services_anchor_a_fingerprint():
    for service in (Rfc3161Service("http://timestamp.digicert.com"),
                    OpenTimestampsService("https://alice.btc.calendar.opentimestamps.org")):
        service.verify(FINGERPRINT, service.anchor(FINGERPRINT))


def available_openssl_builds():
    found = {shutil.which("openssl"), "/usr/bin/openssl" if pathlib.Path("/usr/bin/openssl").exists() else None}
    return sorted(build for build in found if build)


@needs_openssl
@pytest.mark.parametrize("build", available_openssl_builds())
def test_rfc3161_anchor_verifies_with_every_openssl_build_on_this_machine(build):
    check = Rfc3161Service("https://tsa.example/tsr", openssl=build).verify(FINGERPRINT, DIGICERT)
    assert check.signed_on == dt.date(2026, 10, 8)


@needs_openssl
def test_the_signing_day_comes_from_the_signed_part_of_the_anchor_only():
    # The reply's status may carry free text, which is not signed. Put a false date there.
    granted = bytes.fromhex("3003020100")
    assert DIGICERT[:4] == bytes.fromhex("30821768") and DIGICERT[4:9] == granted
    false_date = b"ok\nTime stamp: Jan  1 00:00:00 2020 GMT"
    free_text = bytes([0x0C, len(false_date)]) + false_date                 # a UTF8String
    status = bytes.fromhex("020100") + bytes([0x30, len(free_text)]) + free_text
    status_info = bytes([0x30, len(status)]) + status
    token = DIGICERT[9:]
    forged = bytes([0x30, 0x82]) + (len(status_info) + len(token)).to_bytes(2, "big") + status_info + token

    assert Rfc3161Service("https://tsa.example/tsr").verify(FINGERPRINT, forged).signed_on == dt.date(2026, 10, 8)
