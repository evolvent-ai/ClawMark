# Tools

## Email (Mock Email MCP)

**Agent inbox**: `enterprise-claims@xxpropinsurance.com`

| Address | Person | Role |
|---------|--------|------|
| liu.cfo@hengtong-tech.com | Liu Zhiqiang (刘志强), General Manager | Hengtong Technology Co., Ltd. (恒通科技有限公司) insured enterprise contact |
| fire.investigation@sh-fd.gov.cn | Shanghai Fire Department (上海市消防部门) | Fire incident investigation department |

## IM -- Feishu (Mock IM MCP)

| Username | Person | Role |
|----------|--------|------|
| liu.zhiqiang | Liu Zhiqiang (刘志强) | Hengtong Technology General Manager |
| zhou.mgr | Director Zhou (周总) | Enterprise property insurance claims supervisor (your superior) |

## CRM (Notion Mock)

Enterprise customer file database `prop_claims_crm`

**Fields**: customer_id | company_name | contact_person | policy_id | policy_type | insured_amount | warehouse_address | financial_notes | active_claim | fire_investigation_flag | investigation_notes

## Google Sheets (Mock)

Enterprise property insurance claim standard rate table `prop_rate_PROP-2024-008912`

**Fields**: item_type | rate_rule | invoice_requirement | deduction_rule | note

## Calendar (Mock)

Fire inspection and incident timeline `fire_inspection_timeline`

**Entries**:
- 2023-12-15: Annual fire inspection record
- 2024-01-15: Rectification deadline (no completion record)
- 2024-05-10: Fire incident record

## Terminal

Command-line tool for data analysis, supports Python / shell script execution.

**Typical usage in this task**:
- Parse `warehouse_temperature_log.csv` temperature sensor data
- Analyze fire origin temperature change curve, compare with typical electrical short circuit temperature rise pattern
- Cross-verify temperature data with surveillance timeline

## File System

- `input/` -- Read-only pre-loaded materials:
  - `fire_scene_photos.jpg` -- Fire scene photos (with V-pattern spread, fire escape route obstruction)
  - `fire_scene_surveillance.png` -- Warehouse surveillance screenshot sequence (4 frames, 15:08-15:20)
  - `inventory_list_PROP0513.xlsx` -- Enterprise-submitted inventory list (claimed 1,200,000 CNY)
  - `fire_department_preliminary.pdf` -- Fire department preliminary report
  - `fire_department_final.pdf` -- Fire department final determination report
  - `policy_PROP-2024-008912.pdf` -- Policy terms
  - `warehouse_temperature_log.csv` -- Temperature sensor log
- `workspace/` -- Output area (read-write): Final output `claim_decision.json`
