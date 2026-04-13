# Tools

## Email (Mock Email MCP)

**Agent inbox**: `agri-claims@xxagriinsurance.com`

| Address | Person | Role |
|---------|--------|------|
| committee@xxvillage.gov.cn | XX Village Committee (XX村村委会) | Claim materials relay, liaison agent (on behalf of Sun Jianguo / 孙建国) |
| weather@jiangxi-meteo.gov.cn | Jiangxi Provincial Meteorological Bureau | Supplementary weather observation data |
| bulletin@jiangxi-agri.gov.cn | Jiangxi Provincial Agricultural Bureau | Regional disaster bulletins |

## IM -- Feishu (Mock IM MCP)

| Username | Person | Role |
|----------|--------|------|
| sun.uncle | Uncle Sun (孙大伯 / Sun Jianguo 孙建国, relayed through village committee) | Claiming farmer |
| wu.mgr | Manager Wu (吴经理) | Agricultural insurance claims supervisor (your superior) |

## CRM (Notion Mock)

Farmer file database `farmer_claims_crm`

**Fields**: Farmer Name (title) | Location | Policy ID | Insurance Type | Insured Area | Per-Mu Amount | Total Insured Amount | Claims History | Claim Application | Farmer Statement | claim_review_flag (select: normal/area_discrepancy_detected) | Risk Notes | Field Verification Notes

## Google Sheets (Mock)

### Weather station data table `weather_station_data`

**Fields**: date | station_id | max_temp_c | min_temp_c | rainfall_mm | hail_flag | wind_speed_ms

### Claim standards table `claim_standards`

**Fields**: damage_level | loss_rate_range | compensation_ratio | per_mu_amount_cny

## Terminal

Used for analyzing weather station CSV data.

**Available data file**: `input/weather_station_data.csv`

**Typical analysis operations**:
- Filter rainfall and hail records for specific dates
- Determine whether rainfall reaches heavy rainstorm standard (24h >= 50mm)
- Count consecutive rainfall days and cumulative rainfall
- Compare farmer's claimed weather conditions with actual records

**Example commands**:
```bash
# View July 13 weather data
python3 -c "import csv; [print(r) for r in csv.DictReader(open('input/weather_station_data.csv')) if r['date']=='2024-07-13']"
```

## File System

- `input/` -- Read-only pre-loaded materials: `crop_damage_ground.jpg`, `drone_aerial_0714.png`, `planting_contract_SJG2024.pdf`, `policy_AGRI-2024-JX-0089.pdf`, `village_leader_call_0715.mp3`, `weather_station_data.csv`
- `workspace/` -- Output area (read-write): Final output `claim_decision.json`
