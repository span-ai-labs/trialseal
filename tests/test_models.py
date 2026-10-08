"""Frontier models as shipped: one plain question, asked several times, with everything recorded."""
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import types

import anthropic
import httpx
import httpx2
import openai
import pytest
from google.genai import errors as google_errors
from google.genai import types as google_types

from registry_records import study
from trialforecast import records, universe
from trialforecast.forecasting import Forecast
from trialforecast.models import (
    OUTAGE, ModelForecaster, ModelSpec, ModelUnavailable, Reply, ask_anthropic, ask_google, ask_openai,
    forecasting_prompt, load_keys, model_forecasters, read_models, trial_information, usable_answer,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
BATCH_1 = dt.date(2026, 11, 2)
OPUS = ModelSpec(provider="anthropic", model="claude-opus-5-5", training_cutoff="2026-06",
                 released_on=dt.date(2026, 9, 21), effort="high", input_usd_per_million=4.0, output_usd_per_million=20.0)
GPT = ModelSpec(provider="openai", model="gpt-6.1-sol", training_cutoff="2026-04-30", released_on=dt.date(2026, 9, 28),
                effort="high")
GEMINI = ModelSpec(provider="google", model="gemini-3.8-flash", training_cutoff="2026-03", released_on=dt.date(2026, 9, 2))


def candidate(nct="NCT1", measure="Overall survival (OS)"):
    return universe.flatten(study(nct, measure))


def answer(probability, hazard_ratio, low, high, reasons="For: prior phase 2. Against: crowded class."):
    return (f"{reasons}\n" + json.dumps({"probability_positive": probability, "hazard_ratio": hazard_ratio,
                                          "hazard_ratio_low": low, "hazard_ratio_high": high}))


def answering(*texts, tokens=(1000, 500)):
    """A stand-in for a provider: gives each reply in turn."""
    replies = iter(texts)
    asked = []

    def ask(spec, prompt):
        asked.append((spec, prompt))
        reply = next(replies)
        return reply if isinstance(reply, Reply) else Reply(text=reply, input_tokens=tokens[0], output_tokens=tokens[1],
                                                           model_served=spec.model)

    ask.asked = asked
    return ask


def forecaster(ask, **kwargs):
    return ModelForecaster(OPUS, ask, today=lambda: dt.date(2026, 11, 2), **{"wait": lambda seconds: None, **kwargs})


# --- what every model is shown ---------------------------------------------------------


def test_every_model_is_shown_the_same_trial_information_from_the_registry_record():
    shown = trial_information(candidate())
    for expected in ("NCT1", "A Study of X Versus Y", "Overall survival (OS)", "Acme", "500", "ESTIMATED"):
        assert expected in shown
    assert "results" not in shown.lower()            # nothing about whether results exist
    assert trial_information(candidate()) == shown    # nothing in it depends on the model or the moment


def test_the_arms_are_shown_so_that_experimental_against_control_is_defined():
    s = study("NCT1", "Overall survival")
    s["protocolSection"]["armsInterventionsModule"] = {"armGroups": [
        {"label": "X plus chemotherapy", "type": "EXPERIMENTAL"}, {"label": "Chemotherapy", "type": "ACTIVE_COMPARATOR"}]}
    shown = trial_information(universe.flatten(s))
    assert "EXPERIMENTAL: X plus chemotherapy; ACTIVE_COMPARATOR: Chemotherapy" in shown


def test_the_prompt_asks_one_plain_question_and_is_the_same_every_time():
    prompt = forecasting_prompt(candidate())
    assert trial_information(candidate()) in prompt
    assert "Overall survival (OS)" in prompt and '"probability_positive"' in prompt
    ask = answering(*[answer(0.6, 0.8, 0.6, 1.0)] * 5)
    forecaster(ask).forecast(candidate(), BATCH_1)
    assert {prompt for _, prompt in ask.asked} == {prompt} and len(ask.asked) == 5


def test_changing_the_prompt_means_changing_its_version():
    # If this fails, the wording changed: raise PROMPT_VERSION in models.py, then update the fingerprint here.
    from trialforecast.models import PROMPT_VERSION
    fingerprint = hashlib.sha256(forecasting_prompt(candidate()).encode()).hexdigest()[:16]
    assert (PROMPT_VERSION, fingerprint) == ("1", PROMPT_FINGERPRINT)


PROMPT_FINGERPRINT = "00b540677932f712"


# --- reading an answer -------------------------------------------------------------------


def test_only_the_last_answer_in_a_reply_counts_and_it_must_be_plain_finite_numbers():
    assert usable_answer(answer(0.6, 0.8, 0.6, 1.0)) == (0.6, 0.8, 0.6, 1.0)
    draft_then_final = answer(0.9, 0.7, 0.5, 0.9) + "\nOn reflection:\n" + answer(0.2, 0.95, 0.8, 1.1, reasons="")
    assert usable_answer(draft_then_final) == (0.2, 0.95, 0.8, 1.1)
    for unusable in (
        "No JSON here.", None, "",
        answer(1.7, 0.8, 0.6, 1.0),                                      # not a probability
        answer(0.6, 0.8, 0.9, 1.0),                                      # interval out of order
        answer(0.9, 0.7, 0.5, 0.9) + '\n{"probability_positive": "about 0.2"}',  # a malformed last answer voids the reply
        '{"probability_positive": 0.6, "hazard_ratio": 0.8, "hazard_ratio_low": 0.6, "hazard_ratio_high": Infinity}',
        '{"probability_positive": 0.6, "hazard_ratio": 0.8, "hazard_ratio_low": 0.6, "hazard_ratio_high": 1e400}',
        '{"probability_positive": true, "hazard_ratio": 0.8, "hazard_ratio_low": 0.6, "hazard_ratio_high": 1.0}',
        '{"probability_positive": "0.6", "hazard_ratio": 0.8, "hazard_ratio_low": 0.6, "hazard_ratio_high": 1.0}',
        '{"probability_positive": 0.6, "hazard_ratio": ' + "9" * 400 + ', "hazard_ratio_low": 0.6, "hazard_ratio_high": 1.0}',
    ):
        assert usable_answer(unusable) is None, unusable


# --- combining replies -------------------------------------------------------------------


def test_replies_are_combined_by_the_mean_probability_and_the_geometric_mean_hazard_ratio():
    ask = answering(answer(0.50, 0.70, 0.50, 0.90), answer(0.60, 0.80, 0.60, 1.00), answer(0.70, 0.90, 0.70, 1.10),
                    answer(0.60, 0.80, 0.60, 1.00), answer(0.60, 0.80, 0.60, 1.00))
    forecast = forecaster(ask).forecast(candidate(), BATCH_1)
    assert forecast.probability_positive == pytest.approx(0.60)
    assert forecast.hazard_ratio == pytest.approx(math.exp((math.log(0.7) + 3 * math.log(0.8) + math.log(0.9)) / 5))
    assert forecast.hazard_ratio_low <= forecast.hazard_ratio <= forecast.hazard_ratio_high
    assert forecast.no_forecast is None


def test_everything_needed_to_judge_leakage_and_cost_is_recorded_with_the_forecast():
    texts = [answer(0.6, 0.8, 0.6, 1.0, reasons=f"reply {i}") for i in range(5)]
    forecast = forecaster(answering(*texts, tokens=(1000, 500))).forecast(candidate(), BATCH_1)
    assert (forecast.forecaster, forecast.model, forecast.model_served) == ("claude_opus_5_5", "claude-opus-5-5", "claude-opus-5-5")
    assert forecast.version == "claude-opus-5-5/effort-high/prompt-1/asked-5"
    assert (forecast.model_training_cutoff, forecast.model_released_on, forecast.used_on) == (
        "2026-06", dt.date(2026, 9, 21), dt.date(2026, 11, 2))
    assert forecast.replies == tuple(texts)                           # the raw text of every reply
    assert (forecast.input_tokens, forecast.output_tokens, forecast.provider_failures) == (5000, 2500, 0)
    assert forecast.cost_usd == pytest.approx(5000 * 4 / 1e6 + 2500 * 20 / 1e6)
    assert records.from_line(Forecast, records.to_line(forecast)) == forecast


def test_a_model_cannot_forecast_until_what_its_provider_states_about_it_is_filled_in():
    for unverified in (dict(training_cutoff=None), dict(released_on=None)):
        spec = ModelSpec(**{**dict(provider="anthropic", model="claude-opus-5-5", training_cutoff="2026-06",
                                   released_on=dt.date(2026, 9, 21)), **unverified})
        with pytest.raises(ValueError, match="stated"):
            ModelForecaster(spec, answering())
    with pytest.raises(ValueError, match="at least once"):
        forecaster(answering(), times_asked=0)
    with pytest.raises(ValueError, match="effort"):
        ModelSpec(provider="google", model="gemini-3.8-flash", training_cutoff="2026-03", released_on=BATCH_1, effort="high")


# --- failure to answer ---------------------------------------------------------------------


def test_a_few_unusable_replies_are_left_out_and_recorded():
    ask = answering(answer(0.6, 0.8, 0.6, 1.0), "I cannot say.", answer(0.6, 0.8, 0.6, 1.0),
                    answer(1.7, 0.8, 0.6, 1.0), answer(0.6, 0.8, 0.6, 1.0))
    forecast = forecaster(ask).forecast(candidate(), BATCH_1)
    assert forecast.no_forecast is None and forecast.probability_positive == pytest.approx(0.6)
    assert len(forecast.replies) == 5 and "I cannot say." in forecast.replies


def test_too_few_usable_replies_is_recorded_as_no_forecast_produced():
    refused = Reply(text=None, input_tokens=900, output_tokens=0, failure="refused")
    cut_off = Reply(text="Reasons so far", input_tokens=900, output_tokens=16000, failure="cut off")
    ask = answering(answer(0.6, 0.8, 0.6, 1.0), answer(0.6, 0.8, 0.6, 1.0), refused, "No JSON here.", cut_off)
    forecast = forecaster(ask).forecast(candidate(), BATCH_1)
    assert forecast.no_forecast == "2 of 5 replies gave a usable answer; 3 are needed"
    assert (forecast.probability_positive, forecast.hazard_ratio) == (None, None)
    assert forecast.replies[2] == "[no answer: refused]"
    assert forecast.replies[4] == "[no answer: cut off] Reasons so far"     # whatever text there was is kept
    assert forecast.input_tokens == 3 * 1000 + 2 * 900                     # failed replies are still paid for
    assert records.from_line(Forecast, records.to_line(forecast)) == forecast


def test_a_cut_off_reply_is_not_used_even_if_an_answer_can_be_read_from_it():
    cut_off = Reply(text=answer(0.9, 0.5, 0.4, 0.6), input_tokens=900, output_tokens=16000, failure="cut off")
    ask = answering(cut_off, cut_off, cut_off, answer(0.6, 0.8, 0.6, 1.0), answer(0.6, 0.8, 0.6, 1.0))
    assert forecaster(ask).forecast(candidate(), BATCH_1).no_forecast is not None


def test_an_outage_at_the_provider_is_asked_again_but_a_refusal_is_not():
    unavailable = Reply(text=None, input_tokens=0, output_tokens=0, failure=OUTAGE)
    refused = Reply(text=None, input_tokens=900, output_tokens=0, failure="refused")
    good = answer(0.6, 0.8, 0.6, 1.0)
    waits = []

    ask = answering(unavailable, unavailable, good, good, refused, good, good)
    forecast = forecaster(ask, wait=waits.append).forecast(candidate(), BATCH_1)
    assert len(ask.asked) == 7                           # five replies, the first asked three times
    assert waits == [20, 40]                             # a longer pause before each further attempt
    assert forecast.no_forecast is None and forecast.provider_failures == 2
    assert forecast.replies == (good, good, "[no answer: refused]", good, good)

    still_down = answering(*[unavailable] * 20)
    forecast = forecaster(still_down).forecast(candidate(), BATCH_1)
    assert len(still_down.asked) == 5 * 4                # each: one attempt and three more
    assert forecast.no_forecast == "0 of 5 replies gave a usable answer; 3 are needed"
    assert forecast.replies[0] == f"[no answer: {OUTAGE}]" and forecast.provider_failures == 20


def test_text_a_model_returns_can_always_be_written_to_the_record():
    ask = answering(*[answer(0.6, 0.8, 0.6, 1.0, reasons="broken \ud800 character")] * 5)
    forecast = forecaster(ask).forecast(candidate(), BATCH_1)
    assert records.from_line(Forecast, records.to_line(forecast)) == forecast
    records.to_line(forecast).encode("utf-8")


def test_a_forecast_is_either_complete_or_explicitly_absent():
    common = dict(nct="NCT1", forecaster="x", version="1", batch_date=BATCH_1)
    with pytest.raises(ValueError):
        Forecast(**common, probability_positive=None, hazard_ratio=None, hazard_ratio_low=None, hazard_ratio_high=None)
    with pytest.raises(ValueError):
        Forecast(**common, probability_positive=0.5, hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=1.0,
                 no_forecast="but there is one")
    with pytest.raises(ValueError):
        Forecast(**common, probability_positive=0.5, hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=float("inf"))
    Forecast(**common, probability_positive=None, hazard_ratio=None, hazard_ratio_low=None, hazard_ratio_high=None,
             no_forecast="every reply refused")


# --- the providers' plain interfaces, against replies recorded on 2026-10-08 ---------------------


class Recording:
    """A stand-in for a provider's client method: records what it is sent and gives a recorded reply."""

    def __init__(self, reply):
        self.reply, self.sent = reply, []

    def __call__(self, **request):
        self.sent.append(request)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def recorded(name):
    return json.loads((FIXTURES / name).read_text())


def anthropic_client(reply):
    if isinstance(reply, dict):
        reply = anthropic.types.Message.model_validate(reply)
    create = Recording(reply)
    return types.SimpleNamespace(messages=types.SimpleNamespace(create=create)), create


def openai_client(reply):
    if isinstance(reply, dict):
        reply = openai.types.responses.Response.model_validate(reply)
    create = Recording(reply)
    return types.SimpleNamespace(responses=types.SimpleNamespace(create=create)), create


def google_client(reply):
    if isinstance(reply, dict):
        reply = google_types.GenerateContentResponse.model_validate(reply)
    generate = Recording(reply)
    return types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate)), generate


def test_anthropic_is_asked_with_no_system_prompt_and_no_tools():
    client, create = anthropic_client(recorded("anthropic_message.json"))
    reply = ask_anthropic(OPUS, "the prompt", client=client)
    assert create.sent == [{"model": "claude-opus-5-5", "max_tokens": 16000, "output_config": {"effort": "high"},
                            "messages": [{"role": "user", "content": "the prompt"}]}]
    assert reply == Reply(text="ready", input_tokens=18, output_tokens=4, model_served="claude-opus-5-5")


def test_anthropic_refusals_and_unfinished_answers_are_failures_that_keep_their_text():
    message = recorded("anthropic_message.json")
    for stop_reason, failure in (("refusal", "refused"), ("max_tokens", "cut off"), ("pause_turn", "stopped: pause_turn")):
        client, _ = anthropic_client({**message, "stop_reason": stop_reason})
        reply = ask_anthropic(OPUS, "the prompt", client=client)
        assert (reply.failure, reply.text, reply.input_tokens) == (failure, "ready", 18)


def test_openai_is_asked_with_no_instructions_and_no_tools():
    client, create = openai_client(recorded("openai_response.json"))
    reply = ask_openai(GPT, "the prompt", client=client)
    assert create.sent == [{"model": "gpt-6.1-sol", "input": "the prompt", "max_output_tokens": 16000,
                            "reasoning": {"effort": "high"}}]
    assert (reply.text, reply.input_tokens, reply.output_tokens, reply.failure) == ("ready", 13, 5, None)
    assert reply.model_served.startswith("gpt-6.1-sol")


def test_openai_refusals_are_told_apart_from_answers_that_ran_out_of_room():
    response = recorded("openai_response.json")
    filtered = {**response, "status": "incomplete", "incomplete_details": {"reason": "content_filter"}}
    too_long = {**response, "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    declined = json.loads(json.dumps(response))
    declined["output"][-1]["content"] = [{"type": "refusal", "refusal": "I can't help with that."}]
    for reply_body, failure in ((filtered, "refused"), (too_long, "cut off"), (declined, "refused")):
        client, _ = openai_client(reply_body)
        assert ask_openai(GPT, "the prompt", client=client).failure == failure


def test_google_is_asked_with_the_prompt_alone_and_thinking_counts_as_output():
    client, generate = google_client(recorded("google_response.json"))
    reply = ask_google(GEMINI, "the prompt", client=client)
    assert generate.sent == [{"model": "gemini-3.8-flash", "contents": "the prompt", "config": {"max_output_tokens": 16000}}]
    assert (reply.text, reply.input_tokens, reply.output_tokens, reply.failure) == ("ready", 8, 1 + 79, None)
    assert reply.model_served == "gemini-3.8-flash"


def test_google_stops_are_named_for_what_they_were():
    response = recorded("google_response.json")

    def stopped(finish_reason):
        body = json.loads(json.dumps(response))
        if finish_reason is None:
            del body["candidates"][0]["finish_reason"]
        else:
            body["candidates"][0]["finish_reason"] = finish_reason
        client, _ = google_client(body)
        return ask_google(GEMINI, "the prompt", client=client).failure

    assert stopped("MAX_TOKENS") == "cut off"
    assert stopped("SAFETY") == "refused"
    assert stopped("MALFORMED_FUNCTION_CALL") == "stopped: malformed_function_call"
    assert stopped(None) == "stopped: no reason given"
    client, _ = google_client({**response, "candidates": []})
    assert ask_google(GEMINI, "the prompt", client=client).failure == "stopped: no candidate"


def anthropic_error(status):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIStatusError("error", response=httpx2.Response(status, request=request), body=None)


def openai_error(status):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return openai.APIStatusError("error", response=httpx.Response(status, request=request), body=None)


def test_an_outage_is_a_failed_reply():
    for status in (529, 429, 500):
        client, _ = anthropic_client(anthropic_error(status))
        assert ask_anthropic(OPUS, "the prompt", client=client).failure == OUTAGE
        client, _ = openai_client(openai_error(status if status != 529 else 503))
        assert ask_openai(GPT, "the prompt", client=client).failure == OUTAGE
    client, _ = google_client(google_errors.ServerError(503, {"error": {"message": "high demand"}}))
    assert ask_google(GEMINI, "the prompt", client=client).failure == OUTAGE
    client, _ = google_client(httpx.ConnectError("connection dropped"))
    assert ask_google(GEMINI, "the prompt", client=client).failure == OUTAGE


def test_a_request_the_provider_rejects_stops_everything_instead_of_becoming_a_missing_forecast():
    # A wrong key (401, 403), an unknown model (404), an account out of credit or a malformed request (400, 402, 422):
    # none of these is the model's answer, so none may be recorded as the model producing no forecast.
    for status in (401, 403, 404, 400, 402, 422):
        client, _ = anthropic_client(anthropic_error(status))
        with pytest.raises(ModelUnavailable, match="claude-opus-5-5"):
            ask_anthropic(OPUS, "the prompt", client=client)
        client, _ = openai_client(openai_error(status))
        with pytest.raises(ModelUnavailable):
            ask_openai(GPT, "the prompt", client=client)
    for status in (404, 400):
        client, _ = google_client(google_errors.ClientError(status, {"error": {"message": "rejected"}}))
        with pytest.raises(ModelUnavailable):
            ask_google(GEMINI, "the prompt", client=client)


def test_no_key_never_appears_in_a_failure():
    client, _ = anthropic_client(anthropic.APIConnectionError(message="sk-ant-secret in a message",
                                                              request=httpx2.Request("POST", "https://x")))
    assert "secret" not in ask_anthropic(OPUS, "the prompt", client=client).failure


# --- configuration ---------------------------------------------------------------------------


def test_the_roster_is_read_from_the_study_folder(tmp_path):
    roster = tmp_path / "models.json"
    roster.write_text(json.dumps([{"provider": "anthropic", "model": "claude-opus-5-5", "training_cutoff": "2026-06",
                                   "released_on": "2026-09-21", "effort": "high", "input_usd_per_million": 4.0,
                                   "output_usd_per_million": 20.0, "stated_at": "https://example.test/models"}]))
    assert read_models(roster) == [ModelSpec(**{**OPUS.__dict__, "stated_at": "https://example.test/models"})]
    (made,) = model_forecasters(roster, ask=answering())
    assert (made.name, made.version) == ("claude_opus_5_5", "claude-opus-5-5/effort-high/prompt-1/asked-5")
    roster.write_text(json.dumps([{"provider": "somebody", "model": "x", "training_cutoff": None, "released_on": None}]))
    with pytest.raises(ValueError, match="provider"):
        read_models(roster)


def test_the_studys_own_roster_is_complete():
    study_roster = pathlib.Path(__file__).parents[1] / "study" / "models.json"
    assert [f.name for f in model_forecasters(study_roster, ask=answering())] == [
        "claude_opus_5_5", "gpt_6_1_sol", "gemini_3_8_flash"]


def test_keys_are_read_from_the_environment_file_without_overriding_what_is_set(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('﻿# keys\nANTHROPIC_API_KEY=from-file\nOPENAI_API_KEY=from-file\nexport GOOGLE_API_KEY="quoted=value"\n=stray\n',
                   encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "already-set")
    for name in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    load_keys(env)
    assert (os.environ["ANTHROPIC_API_KEY"], os.environ["OPENAI_API_KEY"], os.environ["GOOGLE_API_KEY"]) == (
        "from-file", "already-set", "quoted=value")
    load_keys(tmp_path / "missing.env")  # no file, nothing to do
