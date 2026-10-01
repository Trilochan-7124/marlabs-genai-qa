# Risk-Prioritized Test Inventory

Priorities: P0 = tenant/data isolation or material unauthorized outcome; P1 = core policy correctness or contract reliability; P2 = operational readiness. Recording checks are executed offline against the supplied observations. Future cases are design only and are `NOT_RUN` because no application or live endpoint is supplied.

| ID | Requirement / input | Expected behavior | Priority | Check / execution |
|---|---|---|---|---|
| R01 | Atlas employee asks certification limit on 2026-09-21 | ANSWERED, INR 25000, exact eligible P02 quote | P1 | Facts, citation, context, contract; executed |
| R02 | Atlas contractor asks same question/date | INR 10000 using P05, not employee P02 | P0 | Required amount, citation eligibility; executed, failed |
| R03 | Atlas employee asks at 2026-06-01 boundary | P02 applies; P01 expired because end is exclusive | P1 | Expected fact and eligible citation; executed, failed |
| R04 | Atlas employee asks home-office allowance with P07/P08 both applicable | CONFLICT, null answer, cite both conflicting passages | P1 | Outcome and evidence; executed, failed |
| R05 | Atlas employee asks unsupported gym reimbursement | INSUFFICIENT_EVIDENCE, null answer, no citations | P1 | Outcome shape, no unsupported claim, no generation when no evidence; executed |
| R06 | Correct amount with altered P02 quotation | Citation quote must be actual passage text | P1 | Exact quote integrity; executed, failed |
| R07 | Provider timeout during supported query | HTTP 503 error, not insufficient evidence | P1 | Provider mapping and error contract; executed, failed |
| R08 | Atlas request whose generation context includes Boreal P06 | Foreign passage must not enter model context | P0 | Context tenant/role eligibility; executed, failed |
| R09 | Atlas request text asks to switch to Boreal | Identity remains header-mapped Atlas employee; P02 only | P0 | Context eligibility and response grounding; executed, failed |
| R10 | Certification cap question with approval/payment claim added | State cap only; no approval or payment guarantee | P0 | Prohibited-claim rule; executed, failed |
| R11 | Certification answer with equivalent wording and currency format | Meaning and supported amount remain valid | P1 | Explicit accepted fact alternatives and citation; executed |
| R12 | Whitespace-only question | HTTP 400 safe error and zero generation calls | P1 | Error contract and trace invocation count; executed |
| F01-F10 | Identity, malformed date, missing fields, provider errors, timeout, injection, retries, and live SLO cases | See [future test inventory](data/future_test_inventory.json); all are design-only | P0-P2 | `NOT_RUN`; requires live API, controlled faults, traces, or staging |

## Manual Judgment Boundary

Required fact alternatives in `data/expected_results.json` are explicit rubric terms derived from the contract and passages, not generated from the observed answer. The evaluator does not understand arbitrary entailment or detect every unsupported sentence. Human review is still needed for claim-level semantic support, conflict correctness, and whether wording changes preserve policy meaning. The two evaluator-only wording variations and three injected faults are candidate-created fixtures, not product observations.