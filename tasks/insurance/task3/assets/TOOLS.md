# Tools

## Email (Mock Email MCP)

Your email address: **flt-claims@xxinsurance.com**

| Address | Person | Role |
|---------|--------|------|
| wangfang2024@gmail.com | Wang Fang | Applicant (policyholder) |
| customerservice@airchina.com.cn | Air China Customer Service | Delay certificate source |
| data@cma.gov.cn | China Meteorological Administration | Satellite imagery / meteorological data source |
| data@caac.gov.cn | CAAC (Civil Aviation Administration of China) | Official flight status data source |

## IM — Feishu (Lark)

Feishu messages are delivered via notifications. You may reply by writing to workspace files.

| Username | Person | Role |
|----------|--------|------|
| wang.fang | Wang Fang | Applicant |
| liu.mgr | Supervisor Liu | Claims manager (your supervisor) |

## CRM (Notion)

Database: `flt_claims_crm`

**Fields**: Customer ID | Name | Policy ID | Claims History | Active Claim | Compliance Flag | Official Delay Reason

## Google Sheets

Rate table: `flt_rate_FLT-2024-003821`

**Fields**: Delay Range | Rate (CNY/Hour) | Covered Reasons | Excluded Reasons

## File System

- `input/` — Read-only: `boarding_pass_CA4112.jpg`, `airline_delay_cert_CA4112.pdf`, `weather_satellite_PEK_20240315.png`, `flight_status_CA4112_CAAC.png`, `policy_FLT-2024-003821.pdf`
- `workspace/` — Output area: write `claim_decision.json`
