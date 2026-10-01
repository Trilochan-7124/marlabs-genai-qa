"""Load evaluation inputs, run checks, and optionally write a report."""

import argparse
import copy
import json
from pathlib import Path

from evaluator.assertions import evaluate_recording
from evaluator.report import build_report, write_report


def _load_json(path):
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def evaluate(data_dir, apply_proposed_fixes=False):
    """Evaluate supplied observations or separately labeled proposed variants."""
    data_dir = Path(data_dir)
    policies = _load_json(data_dir / "policy_corpus.json")
    recordings = _load_json(data_dir / "recordings.json")
    expectations = _load_json(data_dir / "expected_results.json")

    fixes_applied = 0
    if apply_proposed_fixes:
        fixes = _load_json(data_dir / "proposed_fixes.json")
        recordings = copy.deepcopy(recordings)
        recordings_by_id = {item["recording_id"]: item for item in recordings}
        for fix in fixes:
            recording = recordings_by_id[fix["recording_id"]]
            recording["observed"].update(fix.get("observed", {}))
            for field in fix.get("remove_observed_fields", []):
                recording["observed"].pop(field, None)
            recording["trace"].update(fix.get("trace", {}))
            fixes_applied += 1

    recordings_by_id = {item["recording_id"]: item for item in recordings}
    expectations_by_id = {item["recording_id"]: item for item in expectations}
    results = []

    for recording_id, recording in recordings_by_id.items():
        expected = expectations_by_id.get(recording_id)
        if expected is None:
            checks = [{
                "recording_id": recording_id,
                "check_id": "expected_results_exist",
                "risk_area": "assessment_integrity",
                "verdict": "FAIL",
                "expected": "Expected result exists for each recording",
                "observed": None,
                "reason": "No independent expected result exists for this recording.",
            }]
        else:
            checks = evaluate_recording(recording, expected, policies)
        results.append({
            "recording_id": recording_id,
            "status": "FAIL" if any(check["verdict"] == "FAIL" for check in checks) else "PASS",
            "checks": checks,
        })

    for recording_id in sorted(expectations_by_id.keys() - recordings_by_id.keys()):
        results.append({"recording_id": recording_id, "status": "FAIL", "checks": [{
            "recording_id": recording_id,
            "check_id": "recording_exists",
            "risk_area": "assessment_integrity",
            "verdict": "FAIL",
            "expected": "Recording exists for each expected result",
            "observed": None,
            "reason": "Expected result has no corresponding recording.",
        }]})

    report = build_report(results)
    report["assessment_kind"] = (
        "hypothetical_proposed_fixes_not_product_observations"
        if apply_proposed_fixes
        else "supplied_product_observations"
    )
    report["proposed_fixes_applied"] = fixes_applied
    inventory_path = data_dir / "future_test_inventory.json"
    if inventory_path.exists():
        report["designed_tests"] = _load_json(inventory_path)
        report["summary"]["designed_tests_not_run"] = sum(
            item.get("status") == "NOT_RUN" for item in report["designed_tests"]
        )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--apply-proposed-fixes",
        action="store_true",
        help="Evaluate candidate corrections on copies; does not alter supplied recordings.",
    )
    args = parser.parse_args(argv)

    report = evaluate(args.data_dir, apply_proposed_fixes=args.apply_proposed_fixes)
    output_path = args.output or (
        Path("reports/proposed_fix_evaluation_report.json")
        if args.apply_proposed_fixes
        else Path("reports/evaluation_report.json")
    )
    write_report(report, output_path)
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["checks"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())