# Tools

## Email (Mock Email MCP)

**Agent inbox**: `liability-claims@xxpropinsurance.com`

| Address | Person | Role |
|---------|--------|------|
| hr@xindamfg.com | Xinda Manufacturing HR Manager Li (鑫达制造HR李经理) | Policyholder enterprise contact |
| labor@govdept.com | Labor Department (劳动部门) | Work injury determination authority |
| chen.gang.family@email.com | Chen Gang's Family (陈刚家属) | Injured worker's family |

## IM -- Feishu (Mock IM MCP)

| Username | Person | Role |
|----------|--------|------|
| li.hr | HR Manager Li (李经理) | Xinda Manufacturing HR (鑫达制造HR) |
| chen.family | Chen Gang's Family (陈刚家属) | Injured worker's family |
| he.mgr | Manager He (何经理) | Claims supervisor (your superior) |

## CRM (Notion Mock)

Enterprise file database `enterprise_liability_crm`

**Fields**: Enterprise Name | Contact Person | Policy ID | Policy Type | Per-Person Limit | Deductible | Worker Name | Worker Age | Worker Position | Injury Type | Claimed Amount | Accident Date | Accident Description | Equipment Maintenance Record | liability_assessment | Safety Training Notes | Overtime Records | Social Insurance Notes

## Google Sheets (Mock)

Employer liability insurance compensation standards table `liability_compensation_standards`

**Fields**: Item | Standard | Notes

| Item | Standard | Notes |
|------|----------|-------|
| Medical expenses | Actual reimbursement | Cap 300,000 CNY |
| Lost income | Daily wage × days of lost work | Requires medical certificate |
| Disability compensation | Limit × grade ratio | Grade 7: 22% |
| Deductible | 5,000 CNY | Per incident |

## Calendar (Mock)

Worker scheduling system `worker_schedule_system`

**Fields**: date | worker_name | shift_type

## File System

- `input/` -- Read-only pre-loaded materials: `factory_surveillance_0420.png`, `accident_report_XD0420.pdf`, `medical_report_chengang.pdf`, `policy_EL-2024-005678.pdf`, `safety_training_record.png`, `workshop_audio_0420.mp3`
- `workspace/` -- Output area (read-write): Final output `claim_decision.json`
