"""One command that regenerates every registered table and figure: `trialseal-analysis`.

It reads the published seals, the private openings, the adjudication log and the
screening log from a study directory, refuses any forecast that does not match
its seal, and writes the descriptive look and the final analysis once each is due:

    <study>/seals/<batch date>/            seal.json and its two anchors
    <study>/private/<batch date>/          openings.jsonl
    <study>/adjudication/                  the adjudication log, one file per kind of entry
    <study>/screening/screening.jsonl      the screening log
    <study>/study/analyses.jsonl           the record that each registered analysis was run
    <study>/results/                       what this command writes

Which forecaster carries the claim is read from the seals, which have carried the
plan since the first sealing. It is never chosen when the analysis is run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from typing import Iterable

from trialforecast import analysis, records
from trialforecast.adjudication import read_log
from trialforecast.analysis import AlreadyRun, NotDue, NotReady
from trialforecast.anchors import TimestampService, verifying_services
from trialforecast.batch import InvalidForecast
from trialforecast.screening import ScreeningRecord
from trialforecast.sealing import NotInSeal, Plan, SealNotAnchored, TamperedSeal, read_sealed_study
from trialforecast.studyfiles import write_table
from trialforecast.wording import counted

SCREENING_LOG = pathlib.Path("screening") / "screening.jsonl"
ANALYSIS_RECORDS = pathlib.Path("study") / "analyses.jsonl"
SETS_OF_TRIALS = (("forecasters", "primary analysis set"), ("forecasters_all_sponsors", "all sponsors"))
SCORES = ("n_trials", "scored_at_reference", "brier", "log_score", "auc", "reliability", "resolution", "uncertainty")
MODEL_COLUMNS = ("forecaster", "model", "model_served", "training_cutoff", "released_on", "first_used_on",
                 "last_used_on", "trials_scored", "earliest_readout_scored", "latest_readout_scored")
DIFFERENCE = ("mean_diff", "ci_low", "ci_high", "p_two_sided")


# --- tables ------------------------------------------------------------------------


def _write_summary(directory: pathlib.Path, produced: dict, seals: Iterable[str]) -> None:
    """Everything an analysis produced, with the fingerprints of the seals it was made from for a reader to check."""
    directory.mkdir(parents=True, exist_ok=True)
    summary = {**produced, "seals": list(seals)}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, default=str, ensure_ascii=False) + "\n",
                                            encoding="utf-8")


def _write_forecaster_tables(directory: pathlib.Path, produced: dict) -> None:
    """Each forecaster's scores and calibration, on the primary analysis set and on all sponsors, and one row per model."""
    tables = [(label, name, row) for key, label in SETS_OF_TRIALS for name, row in produced[key].items()]
    write_table(directory / "forecasters.csv", ("trials", "forecaster", *SCORES),
                 [(label, name, *(row[score] for score in SCORES)) for label, name, row in tables])
    bin_columns = ("from", "to", "n", "mean_forecast", "share_positive")
    write_table(directory / "calibration.csv", ("trials", "forecaster", *bin_columns),
                 [(label, name, *(bin_[c] for c in bin_columns)) for label, name, row in tables for bin_ in row["calibration"]])
    write_table(directory / "models.csv", MODEL_COLUMNS, [[row[c] for c in MODEL_COLUMNS] for row in produced["models"]])
    _draw_calibration(directory / "calibration.png", produced["forecasters"])


def _difference_cells(difference: dict | None) -> list:
    return [(difference or {}).get(column) for column in DIFFERENCE]


def _write_effect_sizes(directory: pathlib.Path, produced: dict, own: str) -> None:
    """Hazard-ratio scores against each baseline, as reported and with missing hazard ratios counted as no effect."""
    effect_sizes = [("hazard ratios reported", produced["effect_size"]),
                    ("missing counted as no effect", produced["effect_size_missing_as_no_effect"])]
    write_table(
        directory / "effect_size.csv",
        ("analysis", "baseline", "n_trials", "crps_forecaster", "crps_baseline", "interval_score_forecaster",
         "interval_score_baseline", "coverage_forecaster", "coverage_baseline", *DIFFERENCE, "scored_at_baseline",
         "hazard_ratio_awaited", "hazard_ratio_missing", "hazard_ratio_for_another_endpoint"),
        [(label, baseline, e["n_trials"], e["crps"][own], e["crps"][baseline], e["interval_score"][own],
          e["interval_score"][baseline], e["coverage"][own], e["coverage"][baseline],
          *_difference_cells(e["difference"]), len(e["scored_at_baseline"]), len(e["hazard_ratio_awaited"]),
          len(e["hazard_ratio_missing"]), len(e["hazard_ratio_for_another_endpoint"]))
         for label, by_baseline in effect_sizes for baseline, e in by_baseline.items()],
    )


def write_follow_up(directory: pathlib.Path, follow_up: dict, plan: Plan, seals: Iterable[str]) -> None:
    _write_summary(directory, follow_up, seals)
    _write_effect_sizes(directory, follow_up, plan.forecaster)


def write_look(directory: pathlib.Path, look: dict, seals: Iterable[str]) -> None:
    _write_summary(directory, look, seals)
    _write_forecaster_tables(directory, look)


def write_final(directory: pathlib.Path, final: dict, plan: Plan, seals: Iterable[str]) -> None:
    _write_summary(directory, final, seals)
    if final["decision"] == "extended":
        return
    _write_forecaster_tables(directory, final)
    own, reference = plan.forecaster, plan.reference
    comparisons = {"primary": final["primary"], **final["sensitivity"]}
    write_table(
        directory / "comparisons.csv",
        ("comparison", "n_trials", "n_drug_groups", "brier_forecaster", "brier_reference", *DIFFERENCE,
         "scored_at_reference", "forecast_not_before_readout"),
        [(name, c["n_trials"], c["n_drug_groups"], c["brier"][own], c["brier"][reference],
          *_difference_cells(c["difference"]), len(c["scored_at_reference"]), len(c["forecast_not_before_readout"]))
         for name, c in comparisons.items()],
    )
    _write_effect_sizes(directory, final, own)
    for name, label in (("lead_time", "lead_time"), ("versions", "version")):
        write_table(directory / f"{name}.csv", (label, "n_trials", "brier_forecaster", "brier_reference"),
                     [(row[label], row["n_trials"], row["brier"][own], row["brier"][reference]) for row in final[name]])
    _draw_differences(directory / "differences.png", comparisons)


# --- figures -----------------------------------------------------------------------


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")  # files only: no window is opened
    import matplotlib.pyplot as plt

    return plt


def _draw_calibration(path: pathlib.Path, forecasters: dict[str, dict]) -> None:
    """Mean forecast against the share of positive trials, one line per forecaster, on the primary analysis set."""
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], color="0.6", linestyle="--", linewidth=1)
    for name, row in forecasters.items():
        bins = row["calibration"]
        if bins:
            ax.plot([b["mean_forecast"] for b in bins], [b["share_positive"] for b in bins], marker="o", label=name)
    ax.set(xlabel="Forecast probability of a positive trial", ylabel="Share of trials that were positive",
           xlim=(0, 1), ylim=(0, 1))
    if ax.get_legend_handles_labels()[0]:
        ax.legend(frameon=False)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _draw_differences(path: pathlib.Path, comparisons: dict[str, dict]) -> None:
    """The difference in Brier score with its interval, for the primary comparison and each sensitivity analysis."""
    plt = _pyplot()
    shown = [(name, c["difference"]) for name, c in comparisons.items()
             if c["difference"] and c["difference"]["ci_low"] is not None]
    fig, ax = plt.subplots(figsize=(6, 0.5 * len(shown) + 1.2))
    for row, (name, d) in enumerate(reversed(shown)):
        ax.plot([d["ci_low"], d["ci_high"]], [row, row], color="black")
        ax.plot(d["mean_diff"], row, marker="o", color="black")
    ax.axvline(0, color="0.6", linestyle="--", linewidth=1)
    ax.set_yticks(range(len(shown)), [name for name, _ in reversed(shown)])
    ax.set_xlabel("Difference in Brier score, forecaster minus reference (below zero favours the forecaster)")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# --- the command -------------------------------------------------------------------


def _say_final(final: dict, plan: Plan) -> None:
    if final["decision"] == "extended":
        print(f"the study is extended to {final['readouts_to']}: {counted(final['n_trials'], 'trial')} could be "
              f"scored, fewer than {analysis.TRIALS_NEEDED}; nothing has been scored")
        return
    d = final["primary"]["difference"]
    if d is None:
        print("no trial could be scored, so no claim is made")
        return
    interval = "" if d["ci_low"] is None else f" (95% interval {d['ci_low']:.4f} to {d['ci_high']:.4f})"
    estimate = (f"difference in Brier score, {plan.forecaster} minus {plan.reference}: {d['mean_diff']:.4f}{interval} "
                f"on {counted(final['primary']['n_trials'], 'trial')}")
    if final["decision"] == "estimate_only":
        print(f"{estimate}; too few trials or too few drug groups, so no claim is made")
    else:
        print(f"{estimate}; the registered claim is {'supported' if final['claim_supported'] else 'not supported'}")


def main(
    arguments: list[str] | None = None, today: dt.date | None = None,
    services: Iterable[TimestampService] | None = None,
) -> int:
    """Regenerate every registered table and figure that is due: `trialseal-analysis --study <directory>`."""
    parser = argparse.ArgumentParser(prog="trialseal-analysis", description=__doc__.split("\n\n")[0])
    parser.add_argument("--study", default=".", help="the study directory (default: the current directory)")
    parser.add_argument("--hazard-ratios-searched-on", type=dt.date.fromisoformat,
                        help="for the effect-size follow-up: the day the search for hazard ratios was finished")
    options = parser.parse_args(arguments)
    root, today = pathlib.Path(options.study), today or dt.date.today()

    try:
        study = read_sealed_study(root / "seals", root / "private", services or verifying_services())
        if not study.batches:
            print(f"nothing has been sealed under {root / 'seals'}")
            return 0
        log = read_log(root / "adjudication")
        screening = records.read(root / SCREENING_LOG, ScreeningRecord) if (root / SCREENING_LOG).exists() else []
        state = analysis.study_state(study.batches, log, today)
    except (TamperedSeal, SealNotAnchored, NotInSeal, InvalidForecast, OSError, ValueError, TypeError, KeyError) as problem:
        # Whatever is wrong with the files, nothing is scored from them.
        print(f"NOT REGENERATED: {problem}")
        return 1
    print(f"{counted(len(study.batches), 'batch', 'batches')}, {counted(len(state.batches_of), 'trial')} sealed, "
          f"{len(state.results)} with a result, {len(state.awaiting_adjudication)} awaiting adjudication")

    plan, record_file, results_dir = study.plan, root / ANALYSIS_RECORDS, root / "results"
    try:
        try:
            look = analysis.descriptive_look(study.batches, log, plan, today, record_file)
        except NotDue as not_yet:
            print(not_yet)
        else:
            write_look(results_dir / analysis.LOOK, look, study.seals)
            print(f"descriptive look written to {results_dir / analysis.LOOK}")
        try:
            final = analysis.final_analysis(study.batches, log, screening, plan, today, record_file)
        except NotDue as not_yet:
            print(not_yet)
        else:
            write_final(results_dir / analysis.FINAL, final, plan, study.seals)
            _say_final(final, plan)
        try:
            follow_up = analysis.effect_size_follow_up(study.batches, log, plan, today, record_file,
                                                       options.hazard_ratios_searched_on)
        except NotDue as not_yet:
            print(not_yet)
        else:
            write_follow_up(results_dir / analysis.FOLLOW_UP, follow_up, plan, study.seals)
            print(f"effect-size follow-up written to {results_dir / analysis.FOLLOW_UP}")
    except (AlreadyRun, NotReady, ValueError, TypeError, KeyError) as problem:
        # The last three are a record of analyses that cannot be read, or a reference without a forecast.
        print(f"NOT REGENERATED: {problem}")
        return 1
    return 0
