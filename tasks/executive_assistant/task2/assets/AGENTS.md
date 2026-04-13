# Language

All your outputs (CSV files, emails, CRM notes, schedule entries) must be in English.

# Output Specifications

## interview_schedule.csv

**Location**: `interview_schedule.csv`
**Write rule**: Overwrite the same file at each stage update

**Exact header**:
```
candidate_id,candidate_name,date,start_time,end_time,interviewer,room,round,mode
```

**Field definitions**:
| Field | Description | Example |
|-------|-------------|---------|
| candidate_id | C01–C08 | C01 |
| candidate_name | Candidate name | Zhang Ming |
| date | YYYY-MM-DD | 2026-03-25 |
| start_time | HH:MM (24-hour) | 09:00 |
| end_time | HH:MM (start + 45 min) | 09:45 |
| interviewer | A / B / C | A |
| room | 301 / 302 / online | 301 |
| round | 1 / 2 | 1 |
| mode | in-person / online | in-person |

**Example rows**:
```
C01,Zhang Ming,2026-03-25,09:00,09:45,A,301,1,in-person
C01,Zhang Ming,2026-03-25,10:00,10:45,B,302,2,in-person
```

---

## final_schedule.csv

**Location**: `final_schedule.csv`
**Produced**: At the end of Stage 2 as the final archived version
**Schema**: Identical to interview_schedule.csv

---

## Sheets: Transport Reimbursement Ledger

**Sheet name**: `transport_reimbursement`

**Exact header**:
```
candidate_id,candidate_name,origin_city,transport_cost,reimbursable_amount,transfer_fee,reimbursement_status,notes
```

**Field definitions**:
| Field | Description | Example |
|-------|-------------|---------|
| transport_cost | Actual cost incurred (CNY, integer) | 391 |
| reimbursable_amount | Policy-compliant reimbursable amount (CNY, integer) | 73 |
| transfer_fee | Ticket change fee (0 if no change) | 0 |
| reimbursement_status | pending / approved / rejected | rejected |
| notes | Explanation | Business class exceeds policy; reimbursing 2nd-class cap only |

**Example row**:
```
C08,Zhou Tao,Hangzhou,391,73,0,rejected,Business class exceeds policy; reimbursing 2nd-class cap only
```

---

## Candidate Confirmation Emails

**Candidate confirmation emails** must include:
- Interview date and time (precise to the minute)
- Full venue address
- Transportation guidance (nearest subway station / route from train station)
- Contact on arrival (Receptionist Xiao Wang)
