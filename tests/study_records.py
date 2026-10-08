"""Made-up study records for tests: candidates, screenings, adjudications, and stand-in forecasters and services."""
import datetime as dt

from registry_records import study
from trialforecast import universe
from trialforecast.adjudication import Adjudication
from trialforecast.anchors import AnchorCheck, AnchorFailed
from trialforecast.forecasting import BaseRateForecaster, Forecast
from trialforecast.screening import ScreeningRecord
from trialforecast.sealing import Plan, Registration

BATCH_1 = dt.date(2026, 11, 2)
BATCH_2 = dt.date(2026, 12, 1)
SCREENED_ON = dt.date(2026, 10, 30)
ANALYSIS_DATE = dt.date(2028, 5, 2)
EIGHTEEN_MONTHS, TWENTY_FOUR_MONTHS = dt.date(2028, 5, 2), dt.date(2028, 11, 2)   # after the first sealing
BASE_RATES = {"industry/overall_survival": 0.55, "industry/progression": 0.66, "non_industry/overall_survival": 0.3}
REGISTERED = Registration(registry="OSF", url="https://osf.example/abcde", registered_on=dt.date(2026, 10, 31),
                          protocol_sha256="ab" * 32)
PLAN = Plan(forecaster="stand_in", reference="base_rate", effect_size_baselines=("base_rate",))
HAZARD_RATIOS = {
    "industry/overall_survival": (0.84, 0.66, 1.07),
    "industry/progression": (0.70, 0.50, 0.98),
    "non_industry/overall_survival": (0.92, 0.70, 1.20),
}


def candidate(nct, measure="Overall survival", **kwargs):
    return universe.flatten(study(nct, measure, **kwargs))


def screened(nct, decision, on=SCREENED_ON):
    return ScreeningRecord(nct=nct, decision=decision, screened_on=on, evidence="searched press releases and filings")


def adjudicated(nct, adjudicator, outcome, readout=dt.date(2027, 3, 14), **reading):
    """One adjudicator's reading of a press release; `reading` overrides any field, such as the hazard ratio."""
    stopped_without_analysis = outcome == "void"
    fields = dict(
        nct=nct, adjudicator=adjudicator, recorded_on=readout, source_type="press_release_or_filing",
        source="https://example.test/topline", disclosed_on=readout, language="en",
        original_text="Topline results were announced.", translation=None, endpoint_rule="single",
        endpoint_results=() if stopped_without_analysis else (("met",) if outcome == "positive" else ("not_met",)),
        early_stop="no_analysis" if stopped_without_analysis else None, outcome=outcome,
    )
    return Adjudication(**{**fields, **reading})


def both_adjudicated(nct, outcome, readout=dt.date(2027, 3, 14), **reading):
    return [adjudicated(nct, who, outcome, readout, **reading) for who in ("first", "second")]


def base_rate():
    return BaseRateForecaster(BASE_RATES, HAZARD_RATIOS, version="2026-11")


class FixedForecaster:
    """A stand-in forecaster that gives every trial the same answer, or each trial the probability listed for it."""

    def __init__(self, name, probability, version="1", hazard_ratio=(0.8, 0.6, 1.05)):
        self.name, self.version, self._probability, self._hazard_ratio = name, version, probability, hazard_ratio

    def forecast(self, candidate, batch_date):
        nct, (median, low, high) = candidate["nct"], self._hazard_ratio
        probability = self._probability[nct] if isinstance(self._probability, dict) else self._probability
        return Forecast(nct=nct, forecaster=self.name, version=self.version, batch_date=batch_date,
                        probability_positive=probability, hazard_ratio=median, hazard_ratio_low=low,
                        hazard_ratio_high=high)


class Unanswering(FixedForecaster):
    """A stand-in forecaster that produces no forecast, as a model does when its runs fail."""

    def forecast(self, candidate, batch_date):
        return Forecast(nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
                        probability_positive=None, hazard_ratio=None, hazard_ratio_low=None, hazard_ratio_high=None,
                        no_forecast="every run refused", input_tokens=4500, output_tokens=0, cost_usd=0.018)


class FakeService:
    """A stand-in time-stamping service: its anchor is the fingerprint under a method-specific prefix."""

    def __init__(self, method, signed_on=BATCH_1, complete=True):
        self.method, self._signed_on, self._complete = method, signed_on, complete

    def anchor(self, fingerprint):
        return f"{self.method}:{fingerprint}".encode()

    def verify(self, fingerprint, anchor):
        if anchor != f"{self.method}:{fingerprint}".encode():
            raise AnchorFailed(f"{self.method}: not an anchor for {fingerprint}")
        return AnchorCheck(signed_on=self._signed_on if self.method == "rfc3161" else None, complete=self._complete)


def services(signed_on=BATCH_1, complete=True):
    """One stand-in service of each kind, signing on the given day."""
    return [FakeService("rfc3161", signed_on), FakeService("opentimestamps", complete=complete)]


def keys_anywhere(value):
    """Every dictionary key at any depth of a nested result."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_anywhere(v)}
    if isinstance(value, (list, tuple)):
        return {k for v in value for k in keys_anywhere(v)}
    return set()
