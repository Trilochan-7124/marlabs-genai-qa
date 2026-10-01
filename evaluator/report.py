"""Build and persist evaluation reports."""

import json
from datetime import datetime, timezone
from pathlib import Path


def build_report(results):
    """Create a summary with explicit evaluated and not-evaluated counts."""
    checks = [check for result in results for check in result.get("checks", [])]
    verdict_counts = {
        verdict: sum(check.get("verdict") == verdict for check in checks)
        for verdict in ("PASS", "FAIL", "NOT_EVALUATED", "NOT_RUN")
    }
    risk_areas = {}
    for check in checks:
        area = check.get("risk_area", "unspecified")
        counts = risk_areas.setdefault(area, {"PASS": 0, "FAIL": 0, "NOT_EVALUATED": 0, "NOT_RUN": 0})
        verdict = check.get("verdict", "NOT_EVALUATED")
        counts[verdict] = counts.get(verdict, 0) + 1
    for counts in risk_areas.values():
        counts["total"] = sum(counts.values())
    verdict_counts["total"] = sum(verdict_counts.values())
    return {
        "summary": {
            "total": len(results),
            "recordings_with_failures": sum(result["status"] == "FAIL" for result in results),
            "recordings_without_failures": sum(result["status"] == "PASS" for result in results),
            "checks": verdict_counts,
            "risk_areas": risk_areas,
            "designed_tests_not_run": 0,
        },
        "results": results,
    }


def write_report(report, output_path):
    """Write a report as formatted JSON, creating parent folders if needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **report,
    }
    output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return output_path