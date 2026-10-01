"""Reusable assertions for response contracts and policy evidence."""

import re
from datetime import date


CALLERS = {
    "atlas-employee-01": {"tenant": "Atlas", "role": "employee"},
    "atlas-contractor-01": {"tenant": "Atlas", "role": "contractor"},
    "boreal-employee-01": {"tenant": "Boreal", "role": "employee"},
}


def _normalized(value):
    value = re.sub(r"(?<=\d),(?=\d)", "", str(value).casefold())
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _contains_fact(answer, fact):
    normalized_answer = _normalized(answer)
    normalized_fact = _normalized(fact)
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_fact)}(?![a-z0-9])"
    return bool(re.search(pattern, normalized_answer))


def _check(recording_id, check_id, risk_area, passed, expected, observed, reason):
    return {
        "recording_id": recording_id,
        "check_id": check_id,
        "risk_area": risk_area,
        "verdict": "PASS" if passed else "FAIL",
        "expected": expected,
        "observed": observed,
        "reason": reason,
    }


def _is_eligible(policy, request, caller):
    if caller is None or policy is None:
        return False
    try:
        as_of = date.fromisoformat(request["as_of"])
        start = date.fromisoformat(policy["effective_from"])
        end = date.fromisoformat(policy["effective_to"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        policy.get("tenant") == caller["tenant"]
        and policy.get("role") == caller["role"]
        and policy.get("approval_state") == "Approved"
        and start <= as_of < end
    )


def _error_shape_valid(observed):
    body = observed.get("body")
    error = body.get("error") if isinstance(body, dict) else None
    return (
        isinstance(error, dict)
        and isinstance(error.get("code"), str)
        and bool(error["code"].strip())
        and isinstance(error.get("message"), str)
        and bool(error["message"].strip())
        and not any(key in observed for key in ("status", "answer", "citations"))
    )


def evaluate_recording(recording, expected, policies):
    """Evaluate a recording from evidence and expectations, never its ID."""
    recording_id = recording["recording_id"]
    request = recording.get("request", {})
    observed = recording.get("observed", {})
    trace = recording.get("trace", {})
    policy_by_id = {policy["chunk_id"]: policy for policy in policies}
    caller = CALLERS.get(request.get("caller_id"))
    citations = observed.get("citations", [])
    answer = observed.get("answer")
    answer_text = answer if isinstance(answer, str) else ""
    checks = []

    http_status = observed.get("http_status")
    business_status = observed.get("status")
    contract_ok = (
        http_status == 200 and business_status in {"ANSWERED", "INSUFFICIENT_EVIDENCE", "CONFLICT"}
    ) or (http_status in {400, 401, 502, 503} and _error_shape_valid(observed))
    checks.append(_check(recording_id, "response_contract", "response_contract", contract_ok,
        "HTTP 200 business outcome or documented structured HTTP error",
        {"http_status": http_status, "status": business_status, "body": observed.get("body")},
        "HTTP status and body shape follow the contract." if contract_ok else "HTTP status and body do not form a documented outcome."))

    shape_ok = False
    if http_status == 200 and business_status in {"ANSWERED", "INSUFFICIENT_EVIDENCE", "CONFLICT"}:
        shape_ok = isinstance(citations, list)
        if business_status == "ANSWERED":
            shape_ok = shape_ok and bool(answer_text.strip()) and bool(citations)
        elif business_status == "INSUFFICIENT_EVIDENCE":
            shape_ok = shape_ok and answer is None and citations == []
        else:
            shape_ok = shape_ok and answer is None and bool(citations)
    elif http_status != 200:
        shape_ok = _error_shape_valid(observed)
    checks.append(_check(recording_id, "outcome_body_shape", "response_contract", shape_ok,
        "Outcome fields are consistent with status; errors contain only an error object",
        {"status": business_status, "answer": answer, "citations": citations, "body": observed.get("body")},
        "Outcome fields are structurally consistent." if shape_ok else "Outcome fields are inconsistent with the status."))

    outcome_ok = http_status == expected.get("expected_http_status")
    if expected.get("expected_status") is not None:
        outcome_ok = outcome_ok and business_status == expected["expected_status"]
    expected_code = expected.get("expected_error_code")
    actual_code = (observed.get("body") or {}).get("error", {}).get("code")
    if expected_code:
        outcome_ok = outcome_ok and actual_code == expected_code
    checks.append(_check(recording_id, "expected_outcome", "expected_behavior", outcome_ok,
        {"http_status": expected.get("expected_http_status"), "status": expected.get("expected_status"), "error_code": expected_code},
        {"http_status": http_status, "status": business_status, "error_code": actual_code},
        "Observed outcome matches contract and policy-derived expectation." if outcome_ok else "Observed outcome differs from expected behavior."))

    fact_results = []
    for alternatives in expected.get("required_facts", []):
        found = [fact for fact in alternatives if _contains_fact(answer_text, fact)]
        fact_results.append({"alternatives": alternatives, "found": found})
    facts_ok = all(result["found"] for result in fact_results)
    if expected.get("required_facts"):
        checks.append(_check(recording_id, "required_answer_facts", "answer_grounding", facts_ok,
            expected["required_facts"], {"answer": answer_text, "matched": fact_results},
            "Required facts are present using accepted wording." if facts_ok else "At least one required fact is missing."))

    found_prohibited = [claim for claim in expected.get("prohibited_claims", []) if _normalized(claim) in _normalized(answer_text)]
    checks.append(_check(recording_id, "prohibited_claims", "answer_grounding", not found_prohibited,
        {"absent": expected.get("prohibited_claims", [])}, {"found": found_prohibited},
        "No listed prohibited claim appears." if not found_prohibited else "Answer contains a prohibited or unsupported claim."))

    citation_ids = [citation.get("chunk_id") for citation in citations if isinstance(citation, dict)]
    missing_ids = sorted(set(expected.get("required_citation_ids", [])) - set(citation_ids))
    checks.append(_check(recording_id, "expected_citations", "citation_quality", not missing_ids,
        {"required_ids": expected.get("required_citation_ids", [])}, {"citation_ids": citation_ids, "missing": missing_ids},
        "Expected evidence is cited." if not missing_ids else "Expected supporting evidence is absent."))

    citation_issues = []
    for citation in citations:
        chunk_id = citation.get("chunk_id") if isinstance(citation, dict) else None
        policy = policy_by_id.get(chunk_id)
        quote = citation.get("quote") if isinstance(citation, dict) else None
        if policy is None:
            citation_issues.append({"chunk_id": chunk_id, "issue": "unknown citation ID"})
        else:
            if not isinstance(quote, str) or not quote.strip() or quote not in policy["text"]:
                citation_issues.append({"chunk_id": chunk_id, "issue": "quote is not exact passage text"})
            if not _is_eligible(policy, request, caller):
                citation_issues.append({"chunk_id": chunk_id, "issue": "citation ineligible for caller/date"})
    checks.append(_check(recording_id, "citation_integrity_and_eligibility", "citation_quality", not citation_issues,
        "Each citation exists, quotes actual text, and is eligible for caller/date",
        {"citation_ids": citation_ids, "issues": citation_issues},
        "Citations resolve to exact eligible evidence." if not citation_issues else "Citation is fabricated, unknown, or ineligible."))

    context_ids = trace.get("model_context_ids", [])
    context_issues = []
    for chunk_id in context_ids:
        policy = policy_by_id.get(chunk_id)
        if policy is None or not _is_eligible(policy, request, caller):
            context_issues.append({"chunk_id": chunk_id, "issue": "unknown or ineligible generation context"})
    context_check = _check(recording_id, "generation_context_eligibility", "authorization", not context_issues,
        "Only approved tenant/role passages active at as_of; caller must resolve from identity lookup",
        {"model_context_ids": context_ids, "issues": context_issues},
        "All model context is eligible." if caller and not context_issues else "Generation context is unauthorized or caller cannot be verified.")
    if caller is None:
        context_check["verdict"] = "NOT_EVALUATED"
    checks.append(context_check)

    try:
        request_date_valid = date.fromisoformat(request.get("as_of", "")).isoformat() == request.get("as_of")
    except (TypeError, ValueError):
        request_date_valid = False
    invalid_request = not isinstance(request.get("question"), str) or not request["question"].strip() or not request_date_valid
    attempts = trace.get("generation_attempts")
    attempts_ok = isinstance(attempts, int) and 0 <= attempts <= 1 and (not invalid_request or attempts == 0)
    checks.append(_check(recording_id, "generation_attempt_limit", "provider_behavior", attempts_ok,
        "Zero calls for invalid request; at most one call otherwise",
        {"generation_attempts": attempts, "invalid_request": invalid_request},
        "Trace obeys generation invocation limits." if attempts_ok else "Trace shows retry, invalid-request call, or invalid attempt count."))

    event = trace.get("provider_event")
    required_http = {"timeout": 503, "unavailable": 503, "malformed": 502}.get(event)
    provider_ok = required_http is None or http_status == required_http
    checks.append(_check(recording_id, "provider_failure_mapping", "provider_behavior", provider_ok,
        {"provider_event": event, "http_status": required_http}, {"provider_event": event, "http_status": http_status},
        "Provider errors map to documented HTTP errors." if provider_ok else "Provider failure is incorrectly represented as a business outcome."))
    return checks