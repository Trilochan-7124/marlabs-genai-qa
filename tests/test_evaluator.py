import json
import copy
from pathlib import Path

import pytest

from evaluator.assertions import evaluate_recording
from evaluator.evaluator import evaluate
from evaluator.report import write_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assessment_data():
    return (
        json.loads((PROJECT_ROOT / "data" / "policy_corpus.json").read_text(encoding="utf-8")),
        json.loads((PROJECT_ROOT / "data" / "recordings.json").read_text(encoding="utf-8")),
        json.loads((PROJECT_ROOT / "data" / "expected_results.json").read_text(encoding="utf-8")),
    )


def test_all_supplied_recordings_are_evaluated_and_report_is_written(tmp_path):
    report = evaluate(PROJECT_ROOT / "data")

    assert report["summary"]["total"] == 12
    assert report["summary"]["recordings_with_failures"] > 0
    assert report["summary"]["checks"]["FAIL"] > 0
    assert report["summary"]["checks"]["total"] == sum(
        report["summary"]["checks"][verdict] for verdict in ("PASS", "FAIL", "NOT_EVALUATED", "NOT_RUN")
    )
    assert report["summary"]["designed_tests_not_run"] == 10
    assert all(item["status"] == "NOT_RUN" for item in report["designed_tests"])
    assert {result["recording_id"] for result in report["results"]} == {f"{number:02}" for number in range(1, 13)}

    output_path = write_report(report, tmp_path / "nested" / "report.json")
    saved_report = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_report["summary"] == report["summary"]
    assert "generated_at" in saved_report


def test_proposed_corrections_pass_without_changing_supplied_observations():
    policies, recordings, expectations = _assessment_data()
    fixes = json.loads((PROJECT_ROOT / "data" / "proposed_fixes.json").read_text(encoding="utf-8"))
    recordings_by_id = {recording["recording_id"]: recording for recording in recordings}
    expectations_by_id = {expected["recording_id"]: expected for expected in expectations}

    for fix in fixes:
        candidate = copy.deepcopy(recordings_by_id[fix["recording_id"]])
        candidate["observed"].update(fix.get("observed", {}))
        for field in fix.get("remove_observed_fields", []):
            candidate["observed"].pop(field, None)
        candidate["trace"].update(fix.get("trace", {}))
        checks = evaluate_recording(candidate, expectations_by_id[fix["recording_id"]], policies)
        failed = [check for check in checks if check["verdict"] != "PASS"]
        assert not failed, f"{fix['variant_id']} did not pass: {failed}"


def test_proposed_fix_report_resolves_failures_without_relabeling_observations():
    original_report = evaluate(PROJECT_ROOT / "data")
    proposed_report = evaluate(PROJECT_ROOT / "data", apply_proposed_fixes=True)

    assert original_report["summary"]["checks"]["FAIL"] == 23
    assert original_report["assessment_kind"] == "supplied_product_observations"
    assert proposed_report["summary"]["checks"]["FAIL"] == 0
    assert proposed_report["assessment_kind"] == "hypothetical_proposed_fixes_not_product_observations"
    assert proposed_report["proposed_fixes_applied"] == 8


@pytest.mark.parametrize("recording_id,check_id", [
    ("02", "required_answer_facts"),
    ("06", "citation_integrity_and_eligibility"),
    ("09", "generation_context_eligibility"),
    ("10", "prohibited_claims"),
    ("07", "provider_failure_mapping"),
])
def test_relevant_recorded_defects_are_detected(recording_id, check_id):
    report = evaluate(PROJECT_ROOT / "data")
    result = next(item for item in report["results"] if item["recording_id"] == recording_id)

    assert any(check["check_id"] == check_id and check["verdict"] == "FAIL" for check in result["checks"])


@pytest.mark.parametrize("variant", [
    "The yearly certification reimbursement ceiling is INR 25,000.",
    "Annual certification limit: 25000 Indian rupees.",
])
def test_meaning_preserving_answer_variations_pass_fact_check(variant):
    policies, recordings, expectations = _assessment_data()
    recording = copy.deepcopy(next(item for item in recordings if item["recording_id"] == "01"))
    recording["observed"]["answer"] = variant

    checks = evaluate_recording(recording, expectations[0], policies)

    facts_check = next(check for check in checks if check["check_id"] == "required_answer_facts")
    assert facts_check["verdict"] == "PASS"


def test_amount_prefix_does_not_match_larger_amount():
    policies, recordings, expectations = _assessment_data()
    recording = copy.deepcopy(next(item for item in recordings if item["recording_id"] == "01"))
    recording["observed"]["answer"] = "Annual certification limit is INR 125000."

    checks = evaluate_recording(recording, expectations[0], policies)

    facts_check = next(check for check in checks if check["check_id"] == "required_answer_facts")
    assert facts_check["verdict"] == "FAIL"


@pytest.mark.parametrize("fault,check_id", [
    ("fabricated_quote", "citation_integrity_and_eligibility"),
    ("unsupported_approval", "prohibited_claims"),
    ("foreign_context", "generation_context_eligibility"),
])
def test_candidate_faulty_variants_fail_relevant_assertion(fault, check_id):
    policies, recordings, expectations = _assessment_data()
    recording = copy.deepcopy(next(item for item in recordings if item["recording_id"] == "01"))
    if fault == "fabricated_quote":
        recording["observed"]["citations"][0]["quote"] = "The annual limit is INR 99000."
    elif fault == "unsupported_approval":
        recording["observed"]["answer"] += " Your claim is approved and payment is guaranteed."
    else:
        recording["trace"]["model_context_ids"].append("P06")

    checks = evaluate_recording(recording, expectations[0], policies)

    assert any(check["check_id"] == check_id and check["verdict"] == "FAIL" for check in checks)