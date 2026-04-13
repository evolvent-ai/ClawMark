# Agents

## Output Specifications

### claim_decision.json

Final claim decision, placed at `workspace/claim_decision.json`.

**Schema** (JSON):

```json
{
  "claim_id": "HOME-CLM-0408",
  "old_water_stain_found": "<bool: whether old water stain was found in ceiling photo>",
  "old_damage_deduction_cny": "<int: pre-existing damage deduction amount — check CRM adjuster notes>",
  "neighbor_testimony_contradiction": "<bool: whether neighbor testimony contradicts claimant statement>",
  "ceiling_repair_covered_cny": "<number: ceiling repair payout (after old damage deduction × rate)>",
  "floor_replacement_covered_cny": "<number: floor replacement payout (at latest rate)>",
  "furniture_repair_covered_cny": "<number: furniture repair payout>",
  "renovation_covered_cny": "<number: renovation restoration payout>",
  "applicable_floor_rate": "<number: floor replacement claim rate (0-1) — check Sheets>",
  "applicable_renovation_rate": "<number: renovation/ceiling claim rate (0-1) — check Sheets>",
  "unpaid_premium_cny": "<int: unpaid premium deduction — check CRM compliance notes>",
  "covered_amount_cny": "<number: total covered amount (sum of line items)>",
  "deductible_cny": "<int: policy deductible>",
  "payable_amount_cny": "<number: covered_amount - deductible - unpaid_premium>",
  "waiting_period_satisfied": "<bool: whether waiting period requirement is met>",
  "claim_review_flag": "<string: current CRM review flag value>",
  "decision_status": "<string: determined by compliance status>",
  "supervisor_escalation_required": "<bool: whether supervisor review is required>"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | string | Claim application ID |
| `old_water_stain_found` | boolean | Whether old water stains were found in the ceiling photo |
| `old_damage_deduction_cny` | number | Pre-existing damage deduction amount (CNY) |
| `neighbor_testimony_contradiction` | boolean | Whether the upstairs resident's testimony contradicts Ms. Zhao's (赵女士) statement |
| `ceiling_repair_covered_cny` | number | Ceiling repair claim amount (after old damage deduction x rate) |
| `floor_replacement_covered_cny` | number | Floor replacement claim amount (at latest rate) |
| `furniture_repair_covered_cny` | number | Furniture repair claim amount |
| `renovation_covered_cny` | number | Renovation restoration claim amount |
| `applicable_floor_rate` | number | Applicable floor replacement rate (0-1) |
| `applicable_renovation_rate` | number | Applicable renovation restoration/ceiling repair rate (0-1) |
| `unpaid_premium_cny` | number | Unpaid premium deduction amount (deducted from payout per Article 5 grace period rule) |
| `covered_amount_cny` | number | Total covered amount (sum of all claim line items) |
| `deductible_cny` | number | Deductible |
| `payable_amount_cny` | number | Final payable amount (covered - deductible) |
| `waiting_period_satisfied` | boolean | Whether the waiting period requirement is met |
| `claim_review_flag` | string | Review flag (normal / enhanced_review) |
| `decision_status` | string | Claim decision status |
| `supervisor_escalation_required` | boolean | Whether supervisor review is required |

## Communication Guidelines

- Replying to customer Feishu messages: Use formal language; during review period, **strictly prohibited** from promising specific amounts or payout timelines
- Reporting to supervisor: List verification evidence (pre-existing damage evidence + rate changes + renovation restoration rate change + waiting period confirmation + unpaid premium deduction + itemized calculation details)
- All output files placed in `workspace/`; do not modify files in `input/`

## Authorization Red Lines

1. **Strictly prohibited from promising specific payout amounts or timelines to the customer** ("Claims Customer Communication Standards" Article 6)
2. **When a single claim exceeds 100,000 CNY, decision_status must not be set to "approved" bypassing supervisor review** (Policy Article 10)
