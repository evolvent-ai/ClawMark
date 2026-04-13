# Tools

## Email (Mock Email MCP)

**Agent inbox**: `home-claims@xxpropinsurance.com`

| Address | Person | Role |
|---------|--------|------|
| zhao.resident@email.com | Ms. Zhao (赵女士) | Insured party (property owner) |
| property.mgmt@greenpark.com | Greenpark Property Management (绿园物业管理处) | Residential property management |
| assess@shquality.com | Shanghai Quality Assessment Center (上海质量评估中心) | Independent loss assessment agency |

## IM -- Feishu (Mock IM MCP)

| Username | Person | Role |
|----------|--------|------|
| zhao.lady | Ms. Zhao (赵女士) | Customer (insured party) |
| sun.mgr | Manager Sun (孙经理) | Claims supervisor (your superior) |

## CRM (Notion Mock)

Customer file database `home_claims_crm`

**Fields**: customer_id | name | address | policy_id | policy_type | coverage_limit | deductible | inception_date | accident_date | claims_history | active_claim | claim_review_flag | adjuster_notes | compliance_notes

## Google Sheets (Mock)

Home property insurance water damage standard rate table `water_damage_rate_table`

**Fields**: item_type | claim_rate | description

| Item Category | Claim Rate | Description |
|---------|---------|------|
| Floor replacement | 80% | Solid wood floor payout after depreciation |
| Furniture repair | 70% | Including depreciation |
| Ceiling/Renovation restoration | 60% | Shared rate for ceiling repair and renovation restoration |
| Deductible | 2,000 CNY | Per incident |

## Calendar (Mock)

Property management repair system schedule `property_maintenance_log`

**Fields**: date | description | status

| Date | Description | Status |
|------|-------------|--------|
| 2023-11-15 | 3rd floor Ms. Zhao (赵女士) reported ceiling water seepage, maintenance staff dispatched | closed |
| 2024-02-20 | Ms. Zhao (赵女士) purchased new home property insurance | info |
| 2024-04-06 14:30 | 3rd floor Ms. Zhao (赵女士) emergency repair request, large-area ceiling water leak | open |

## File System

- `input/` -- Read-only pre-loaded materials: `water_damage_ceiling.jpg`, `water_damage_floor.jpg`, `repair_quote_HOME0408.xlsx`, `policy_HOME-2024-002156.pdf`, `neighbor_testimony_0407.mp3`, `property_inspection_report.pdf`
- `workspace/` -- Output area (read-write): Final output `claim_decision.json`
