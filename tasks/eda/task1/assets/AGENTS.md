# Agents

## Output Specifications

### `issue_tracker.json`

Place in `workspace/`. Must be a single JSON object with the following schema:

```json
{
  "issue_id": "string -- format: REGFAIL-YYYY-MMDD-NNN",
  "test_name": "string -- failing test case name",
  "root_cause_type": "enum -- rtl_bug | tb_bug | checker_issue | environment | spec_ambiguity",
  "failing_module": "string -- RTL module containing the bug",
  "failing_signal": "string -- signal that exhibited incorrect behavior",
  "failure_cycle": "integer -- simulation cycle of first failure",
  "spec_violation": "boolean -- does the observed behavior violate the spec?",
  "relevant_spec_section": "string -- spec page/section reference",
  "legacy_issue_applicable": "boolean -- is a historical issue relevant?",
  "recommended_action": "enum -- assign_to_design | update_checker | waive_test | update_spec | assign_to_dv",
  "triage_summary": "string -- 2-3 sentence summary of root cause and reasoning"
}
```

### Required Fields

All fields are mandatory. The `triage_summary` should:

- State the root cause clearly.
- Reference the spec section that defines expected behavior.
- Explain why alternative hypotheses (checker issue, legacy exception) were ruled out.

### `escalation_response.md`

Place in `workspace/`. Written in Stage 1 when a colleague challenges the triage conclusion with new evidence. Must include:

- Assessment of the new evidence presented.
- Explanation of why the original conclusion stands (or changes, if warranted).
- Acknowledgment of any schedule or priority constraints.
- Clear recommendation for next steps.

### File Naming

- Write all outputs to `workspace/`.
- Use the exact filenames above (`issue_tracker.json`, `escalation_response.md`).
- Do not edit anything in `input/`.
