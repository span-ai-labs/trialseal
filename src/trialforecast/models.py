"""Frontier models as shipped, used as forecasters.

Each model is asked one plain question through its provider's ordinary interface:
no system prompt, no tools, no retrieval. Every model sees the same trial
information, taken from the frozen registry record. A trial is asked about several
times and the usable answers are combined by a fixed rule. A refusal is never
passed to another model: it is recorded as a failed reply, so a forecast is always
the named model's own.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import pathlib
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from trialforecast.forecasting import Candidate, Forecast, valid_numbers

PROMPT_VERSION = "1"  # raise whenever the wording of the prompt changes; a test pins its fingerprint
MAX_OUTPUT_TOKENS = 16000
TIMES_ASKED = 5
USABLE_SHARE_NEEDED = 0.6  # of the times asked, the share that must give a usable answer
FURTHER_ATTEMPTS = 3  # after an outage at the provider; never after the model's own refusal
PAUSE_SECONDS = 20

OUTAGE = "provider unavailable"  # the one failure that is asked again: it says nothing about the model
PROVIDERS_WITHOUT_EFFORT = ("google",)


class ModelUnavailable(Exception):
    """A model cannot be asked: a missing or rejected key, an account out of credit, a request the provider
    will not accept, or a model name it does not know.

    This stops the batch. Recording it as "no forecast produced" would make a
    configuration mistake a permanent part of the study's record.
    """


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    training_cutoff: str | None  # as the provider states it
    released_on: dt.date | None
    effort: str | None = None  # the provider's reasoning-effort setting, where it has one
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None
    stated_at: str | None = None  # where the cutoff, release date and prices were read

    def __post_init__(self) -> None:
        if self.effort and self.provider in PROVIDERS_WITHOUT_EFFORT:
            raise ValueError(f"{self.model}: no effort setting is passed to {self.provider} models; leave it empty")

    def cost(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.input_usd_per_million is None or self.output_usd_per_million is None:
            return None
        return (input_tokens * self.input_usd_per_million + output_tokens * self.output_usd_per_million) / 1e6


@dataclass(frozen=True)
class Reply:
    """What came back from asking a model once: its text, or the reason there is no answer."""

    text: str | None
    input_tokens: int
    output_tokens: int
    failure: str | None = None
    model_served: str | None = None


Ask = Callable[[ModelSpec, str], Reply]


# --- what a model is shown -----------------------------------------------------------------

_SHOWN = (
    ("Registry number", "nct"), ("Acronym", "acronym"), ("Title", "brief_title"), ("Conditions", "conditions"),
    ("Interventions", "interventions"), ("Arms", "arms"), ("Lead sponsor", "lead_sponsor"),
    ("Collaborators", "collaborators"), ("Phase", "phases"), ("Masking", "masking"),
    ("Enrolment", "enrollment"), ("Enrolment is", "enrollment_type"), ("Start date", "start_date"),
    ("Registry completion date", "primary_completion_date"), ("Registry completion date is", "primary_completion_type"),
    ("Status", "status"), ("Primary outcome measures", "primary_outcomes"),
    ("Primary outcome time frames", "primary_time_frames"),
)


def _stated(value: Any) -> str:
    # A candidate read from a table carries NaN where the registry had nothing.
    missing = value is None or value == "" or (isinstance(value, float) and math.isnan(value))
    if missing:
        return "not stated"
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def trial_information(candidate: Candidate) -> str:
    """The trial as every model sees it: fixed fields of the frozen registry record, in a fixed order."""
    return "\n".join(f"{label}: {_stated(candidate.get(field))}" for label, field in _SHOWN)


def forecasting_prompt(candidate: Candidate) -> str:
    return (
        "A randomised phase 3 cancer trial has not yet reported its primary result. "
        "Forecast how it will read out, using only what you already know.\n\n"
        f"Trial record from ClinicalTrials.gov:\n{trial_information(candidate)}\n\n"
        "Two forecasts are needed.\n"
        "1. The probability that the trial is positive: that its first public primary analysis reports a "
        "statistically significant benefit on its primary endpoint. Where several primary endpoints each "
        "suffice, one is enough; where they are co-primary, all are needed.\n"
        f"2. The hazard ratio that will be reported for this endpoint, experimental arm against control: "
        f"{candidate['scored_endpoint']}. Give your median estimate and an 80% interval.\n\n"
        "Give your main reasons for and against in a few sentences. Then end with one line of JSON in exactly "
        "this form, with your own numbers:\n"
        '{"probability_positive": 0.00, "hazard_ratio": 0.00, "hazard_ratio_low": 0.00, "hazard_ratio_high": 0.00}'
    )


_JSON_OBJECT = re.compile(r"\{[^{}]*\}")
_ASKED_FOR = ("probability_positive", "hazard_ratio", "hazard_ratio_low", "hazard_ratio_high")


def _not_a_number(name: str) -> float:
    raise ValueError(f"{name} is not a number a forecast can hold")


def last_json_object(text: str | None) -> str | None:
    """The last flat JSON object in a reply, as text. Only the last counts: a draft is never taken for the answer."""
    found = _JSON_OBJECT.findall(text or "")
    return found[-1] if found else None


def usable_answer(text: str | None) -> tuple[float, float, float, float] | None:
    """The four numbers from the last JSON object in a reply, if they form a valid forecast.

    Only the last object counts: an earlier draft is never taken in place of a
    final answer that turned out malformed.
    """
    final = last_json_object(text)
    if final is None:
        return None
    try:
        stated = json.loads(final, parse_constant=_not_a_number)
        numbers = tuple(stated[name] for name in _ASKED_FOR)
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in numbers):
            return None
        probability, hazard_ratio, low, high = (float(x) for x in numbers)
    except (ValueError, TypeError, KeyError, OverflowError):
        return None
    return (probability, hazard_ratio, low, high) if valid_numbers(probability, hazard_ratio, low, high) else None


def ask_through_outages(ask: Ask, spec: ModelSpec, prompt: str, wait: Callable[[float], None] = time.sleep) -> tuple[Reply, int]:
    """One reply, and how many attempts were lost to outages at the provider before it."""
    lost = 0
    reply = ask(spec, prompt)
    while reply.failure == OUTAGE and lost < FURTHER_ATTEMPTS:
        lost += 1
        wait(PAUSE_SECONDS * lost)
        reply = ask(spec, prompt)
    return reply, lost + (reply.failure == OUTAGE)


# --- a model as a forecaster ---------------------------------------------------------------


class ModelForecaster:
    """Asks one model about a trial several times and combines the usable answers.

    The probability is the mean of the usable answers. The hazard ratio and each
    end of its interval are geometric means, which is the mean on the log scale the
    forecast is scored on. With too few usable answers the record says no forecast
    was produced. A reply that was refused or cut off is not used, whatever its text.
    """

    def __init__(
        self,
        spec: ModelSpec,
        ask: Ask,
        times_asked: int = TIMES_ASKED,
        today: Callable[[], dt.date] = lambda: dt.datetime.now(dt.timezone.utc).date(),
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        if spec.training_cutoff is None or spec.released_on is None:
            raise ValueError(
                f"{spec.model}: the training cutoff and release date stated by its provider must be filled in first")
        if times_asked < 1:
            raise ValueError("a model must be asked at least once")
        self._spec, self._ask, self._times_asked, self._today, self._wait = spec, ask, times_asked, today, wait
        self.name = re.sub(r"[^a-z0-9]+", "_", spec.model.lower()).strip("_")
        effort = f"/effort-{spec.effort}" if spec.effort else ""
        self.version = f"{spec.model}{effort}/prompt-{PROMPT_VERSION}/asked-{times_asked}"

    def forecast(self, candidate: Candidate, batch_date: dt.date) -> Forecast:
        prompt = forecasting_prompt(candidate)
        asked = [ask_through_outages(self._ask, self._spec, prompt, self._wait) for _ in range(self._times_asked)]
        replies = [reply for reply, _ in asked]
        answers = [found for r in replies if r.failure is None and (found := usable_answer(r.text)) is not None]
        needed = math.ceil(self._times_asked * USABLE_SHARE_NEEDED)
        spec = self._spec
        input_tokens = sum(r.input_tokens for r in replies)
        output_tokens = sum(r.output_tokens for r in replies)
        served = sorted({r.model_served for r in replies if r.model_served})
        recorded = dict(
            nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
            model=spec.model, model_served=", ".join(served) or None,
            model_training_cutoff=spec.training_cutoff, model_released_on=spec.released_on, used_on=self._today(),
            replies=tuple(_as_recorded(r) for r in replies), provider_failures=sum(lost for _, lost in asked),
            input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=spec.cost(input_tokens, output_tokens),
        )
        if len(answers) < needed:
            return Forecast(
                **recorded, probability_positive=None, hazard_ratio=None, hazard_ratio_low=None,
                hazard_ratio_high=None,
                no_forecast=f"{len(answers)} of {self._times_asked} replies gave a usable answer; {needed} are needed",
            )
        probabilities, medians, lows, highs = zip(*answers)
        return Forecast(
            **recorded, probability_positive=sum(probabilities) / len(answers),
            hazard_ratio=_geometric_mean(medians), hazard_ratio_low=_geometric_mean(lows),
            hazard_ratio_high=_geometric_mean(highs),
        )


def _geometric_mean(values: tuple[float, ...]) -> float:
    return math.exp(sum(math.log(v) for v in values) / len(values))


def writable(text: str | None) -> str:
    """A reply's text as it can be stored: characters that cannot be written as UTF-8 are replaced, nothing else."""
    return (text or "").encode("utf-8", "replace").decode("utf-8")


def _as_recorded(reply: Reply) -> str:
    text = writable(reply.text)
    if reply.failure is None:
        return text
    return f"[no answer: {reply.failure}]" + (f" {text}" if text else "")


# --- the providers' plain interfaces -----------------------------------------------------------


def _failed(reason: str, text: str | None = None, tokens: tuple[int, int] = (0, 0), served: str | None = None) -> Reply:
    return Reply(text=text, input_tokens=tokens[0], output_tokens=tokens[1], failure=reason, model_served=served)


def _after_error(spec: ModelSpec, status: int | None) -> Reply:
    """What an error from a provider means. Only its status is used, never its message, which may quote a key.

    An outage is a failed reply that is asked again. Anything else the provider
    rejects stops everything: a wrong key, an unknown model, an account out of
    credit or a request it will not accept is a fault in the setup, and says
    nothing about what the model would have forecast.
    """
    if status is None or status in (408, 409, 429) or status >= 500:
        return _failed(OUTAGE)
    raise ModelUnavailable(f"{spec.provider} would not serve {spec.model} (status {status}): check the key, the "
                           f"account's credit and the model's name")


_clients: dict[str, Any] = {}


def _client(provider: str, make: Callable[[], Any]) -> Any:
    # One client per provider for the life of the process.
    if provider not in _clients:
        _clients[provider] = make()
    return _clients[provider]


def ask_anthropic(spec: ModelSpec, prompt: str, client: Any = None) -> Reply:
    import anthropic

    client = client or _client("anthropic", anthropic.Anthropic)
    request: dict[str, Any] = {"model": spec.model, "max_tokens": MAX_OUTPUT_TOKENS}
    if spec.effort:
        request["output_config"] = {"effort": spec.effort}
    request["messages"] = [{"role": "user", "content": prompt}]
    try:
        message = client.messages.create(**request)
    except anthropic.APIStatusError as error:
        return _after_error(spec, error.status_code)
    except anthropic.APIError:  # connection failures, timeouts, replies the library could not read
        return _after_error(spec, None)
    tokens = (message.usage.input_tokens, message.usage.output_tokens)
    text = "".join(block.text for block in message.content if block.type == "text") or None
    if message.stop_reason != "end_turn":
        reason = {"refusal": "refused", "max_tokens": "cut off"}.get(message.stop_reason, f"stopped: {message.stop_reason}")
        return _failed(reason, text, tokens, message.model)
    if text is None:
        return _failed("no text", None, tokens, message.model)
    return Reply(text, *tokens, model_served=message.model)


def ask_openai(spec: ModelSpec, prompt: str, client: Any = None) -> Reply:
    import openai

    client = client or _client("openai", openai.OpenAI)
    request: dict[str, Any] = {"model": spec.model, "input": prompt, "max_output_tokens": MAX_OUTPUT_TOKENS}
    if spec.effort:
        request["reasoning"] = {"effort": spec.effort}
    try:
        response = client.responses.create(**request)
    except openai.APIStatusError as error:
        return _after_error(spec, error.status_code)
    except openai.APIError:
        return _after_error(spec, None)
    tokens = (response.usage.input_tokens, response.usage.output_tokens) if response.usage else (0, 0)
    text = response.output_text or None
    declined = any(
        getattr(part, "type", None) == "refusal"
        for item in response.output if getattr(item, "type", None) == "message" for part in item.content
    )
    if declined:
        return _failed("refused", text, tokens, response.model)
    if response.status != "completed":
        why = getattr(response.incomplete_details, "reason", None)
        reason = "refused" if why == "content_filter" else "cut off" if response.status == "incomplete" else f"stopped: {response.status}"
        return _failed(reason, text, tokens, response.model)
    if text is None:
        return _failed("no text", None, tokens, response.model)
    return Reply(text, *tokens, model_served=response.model)


_GOOGLE_REFUSALS = ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY")


def ask_google(spec: ModelSpec, prompt: str, client: Any = None) -> Reply:
    import httpx
    from google import genai
    from google.genai import errors

    def make() -> Any:
        if not os.environ.get("GOOGLE_API_KEY"):
            raise ModelUnavailable(f"no GOOGLE_API_KEY is set, so {spec.model} cannot be asked")
        return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    client = client or _client("google", make)
    try:
        response = client.models.generate_content(
            model=spec.model, contents=prompt, config={"max_output_tokens": MAX_OUTPUT_TOKENS})
    except errors.APIError as error:
        return _after_error(spec, error.code if isinstance(error.code, int) else None)
    except httpx.TransportError:
        return _after_error(spec, None)
    counted = response.usage_metadata
    tokens = (
        (counted.prompt_token_count or 0, (counted.candidates_token_count or 0) + (counted.thoughts_token_count or 0))
        if counted else (0, 0)
    )  # thinking is billed as output
    served = response.model_version
    if not response.candidates:
        return _failed("stopped: no candidate", None, tokens, served)
    text = response.text or None
    finished = response.candidates[0].finish_reason
    if finished is None:
        return _failed("stopped: no reason given", text, tokens, served)
    if finished.name != "STOP":
        reason = ("cut off" if finished.name == "MAX_TOKENS" else "refused" if finished.name in _GOOGLE_REFUSALS
                  else f"stopped: {finished.name.lower()}")
        return _failed(reason, text, tokens, served)
    if text is None:
        return _failed("no text", None, tokens, served)
    return Reply(text, *tokens, model_served=served)


PROVIDERS: dict[str, Ask] = {"anthropic": ask_anthropic, "openai": ask_openai, "google": ask_google}


def ask_provider(spec: ModelSpec, prompt: str) -> Reply:
    return PROVIDERS[spec.provider](spec, prompt)


# --- configuration -----------------------------------------------------------------------------


def read_models(roster: pathlib.Path) -> list[ModelSpec]:
    """The models named in the study folder, each with what its provider states about it."""
    specs = []
    for entry in json.loads(roster.read_text(encoding="utf-8")):
        if entry.get("provider") not in PROVIDERS:
            raise ValueError(f"{roster}: unknown provider {entry.get('provider')!r}; expected one of {sorted(PROVIDERS)}")
        released = entry.get("released_on")
        specs.append(ModelSpec(**{**entry, "released_on": dt.date.fromisoformat(released) if released else None}))
    return specs


def model_forecasters(roster: pathlib.Path, ask: Ask = ask_provider) -> list[ModelForecaster]:
    """One forecaster for each model in the roster."""
    return [ModelForecaster(spec, ask) for spec in read_models(roster)]


def load_keys(env_file: pathlib.Path) -> None:
    """Put the keys the setup wizard saved into the environment, without replacing any already set."""
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        name, separator, value = line.strip().removeprefix("export ").partition("=")
        name, value = name.strip(), value.strip()
        if not separator or not name or name.startswith("#"):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(name, value)
