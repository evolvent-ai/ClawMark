# Output Specifications

## placement_plan.json

Primary deliverable. Write to `/workspace/placement_plan.json` (workspace root).

**Schema**:

```json
{
  "redundant_roles": [
    {
      "role_group": "team_lead_merge",
      "source_roles": ["Team Lead A", "Team Lead B"],
      "target_role": "New Team Lead",
      "available_slots": 1,
      "candidate_pool": ["E01", "E02"]
    }
  ],
  "placements": [
    {
      "employee_id": "E01",
      "employee_name": "Zhang San",
      "current_role": "Team Lead A",
      "recommended_target_role": "New Team Lead",
      "placement_status": "recommended",
      "policy_compliant": true,
      "risk_flags": ["critical_talent_retention"],
      "notes": ""
    }
  ],
  "org_stability_risk": {
    "risk_level": "medium",
    "risk_signals": ["employee_layoff_rumor", "yellow_attrition_risk"],
    "notes": ""
  }
}
```

### Field Definitions

**redundant_roles** (array): Structured redundancy findings from org comparison.
- `role_group` (string): Identifier for the redundancy group
- `source_roles` (array of strings): Legacy role names being merged
- `target_role` (string): New merged role name
- `available_slots` (integer): Number of seats in the merged structure
- `candidate_pool` (array of strings): Employee IDs competing for the seat(s)

**placements** (array, exactly 4 entries for E01-E04):
- `employee_id` (string): One of `E01`, `E02`, `E03`, `E04`
- `employee_name` (string): Employee full name
- `current_role` (string): Pre-merger role title
- `recommended_target_role` (string): Post-merger recommended role
- `placement_status` (enum): `recommended` | `alternate_placement` | `retain`
- `policy_compliant` (boolean): `true` or `false`
- `risk_flags` (array of strings): Machine-readable flags, suggested values:
  - `manager_performance_conflict`
  - `critical_talent_retention`
  - `yellow_attrition_risk`
  - `employee_layoff_rumor`
- `notes` (string): Free-text rationale

**Expected final ground truth**:
- `E01` -> `New Team Lead` / `recommended`
- `E02` -> `Integration Program Manager` / `alternate_placement`
- `E03` -> `Senior Operations Specialist` / `retain`
- `E04` -> `Senior Operations Specialist` / `retain`

**org_stability_risk** (object, required after Stage 2):
- `risk_level` (enum): `low` | `medium` | `high`
- `risk_signals` (array of strings): Machine-readable risk signal identifiers
- `notes` (string): Description of risk and recommended actions

## ATS Updates

For every employee, write to the Notion database `org_restructuring_placement_2024`:

- `Target Role` (rich_text): Recommended post-merger role
- `Placement Status` (select): Current placement decision state
- `Risk Level` (select): `low` | `medium` | `high`
- `Notes` (rich_text): Structured rationale

Notes should remain concise but structured enough for deterministic review.

## Email Communication

- Stage 0 email to HRBP: Summarize redundancy finding and first-pass placement plan. Attach `placement_plan.json`.
- Stage 1 email to HRBP: Explicitly name the unique TL recommendation (E01 Zhang San) and the alternate placement for E02 Li Si. Attach the updated `placement_plan.json`.
- Stage 2 email to HR VP: Describe the rumor-driven stability risk as an **unverified concern**, not a confirmed layoff decision.

## Red Lines

- Do NOT modify files in `input/` -- that directory is read-only source evidence.
- Do NOT mark any employee as `offboard`, `terminated`, `laid_off`, or equivalent.
- Do NOT present layoff rumors as confirmed fact.
