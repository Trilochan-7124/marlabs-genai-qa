# Marlabs GenAI QA Assessment

Offline assessment of the supplied synthetic candidate-assessment corpus and twelve recorded observations. It does not call or implement the assistant.

## Setup

Use Python 3.9 or newer, then install the test dependency:

```powershell
python -m pip install -r requirements.txt
```

## Run

From this project root, evaluate all twelve observations and write the JSON report:

```powershell
python -m evaluator.evaluator
```

The command exits `0` only when there are no failed checks, and `1` when any evaluated check fails. The report includes each check's recording ID, rule, expected and observed values, verdict, reason, risk-area counts, and future tests marked `NOT_RUN`. Input and output locations can be overridden:

```powershell
python -m evaluator.evaluator --data-dir data --output reports/evaluation_report.json
```

To evaluate the eight candidate-created corrections on copies and write a separate hypothetical report:

```powershell
python -m evaluator.evaluator --apply-proposed-fixes
```

This writes `reports/proposed_fix_evaluation_report.json` and should exit `0` when all proposed variants satisfy the rubric. It does not change `data/recordings.json` or prove the product has been fixed; the normal command continues to report failures in the supplied observations.

From Windows CMD at any working directory, use the included launcher (it changes to the project directory automatically):

```cmd
D:\Practice\marlabs-genai-qa\run_assessment.cmd --apply-proposed-fixes
```

Test the evaluator itself with:

```powershell
pytest
```

## Assessment Files

- `data/policy_corpus.json`: policy metadata and passage text transcribed from the assessment.
- `data/recordings.json`: faithful request, response, citation, and trace observations. These are not edited by the evaluator.
- `data/expected_results.json`: independent expected outcomes and rationales.
- `data/proposed_fixes.json`: separate candidate-created corrected variants used only for regression tests; not product observations.
- `data/future_test_inventory.json`: additional live-system cases explicitly marked `NOT_RUN`.
- `test_inventory.md`: risk-ranked inventory for all supplied recordings and future test design.
- `reports/evaluation_report.json`: generated check-level result report.
- `defects/defect_report.md`: five evidence-based defect reports and a pilot decision.

Phrase facts use explicit accepted alternatives and token-boundary matching, with comma-normalized amounts. Citations are checked against exact corpus text and caller/date eligibility. The evaluator does not prove arbitrary claim entailment; manual semantic review remains necessary. The proposed-fix test proves these candidate variants satisfy the offline rubric; it does not establish that the product has been fixed.

## Limits and Handoff

All evidence is synthetic and offline. No endpoint, application source, or production telemetry was supplied, so API integration, authentication, real latency, availability, load, and prevalence remain unverified. Passing evaluator tests prove only the checker behavior, not assistant quality. Overall pass percentage is not a release metric for this intentionally risk-weighted sample.

Time spent: not tracked. AI assistance: GitHub Copilot was used to transcribe the provided requirements into a local evaluator and test pack; expected outcomes were derived from the supplied contract and policy passages and should receive independent review. No public repository was created and no recruitment email was sent as part of this local assessment.