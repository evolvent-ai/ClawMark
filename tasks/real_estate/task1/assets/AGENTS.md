# Output File Spec

All output files go to `workspace/outputs/`. Use UTF-8, comma-separated CSV.

## Primary Output: `outputs/site_shortlist.csv`

The site screening shortlist. One row per evaluated site.

**Schema:**
```
site_id,site_name,area_listed,area_measured,rent_monthly,status,blocker_type,score,recommendation
```

- `site_id`: Site identifier (e.g., S01, S02, ... S08)
- `site_name`: Mall and unit name
- `area_listed`: Area (sqm) as listed in CRM
- `area_measured`: Area (sqm) as measured from floor plans; same as area_listed if no floor plan discrepancy found
- `rent_monthly`: Current monthly rent (CNY)
- `status`: one of {`recommended`, `conditional`, `blocked`, `rejected`, `over_budget`}
- `blocker_type`: one of {`none`, `no_drainage`, `competitor_nearby`, `no_accessible_entry`, `area_mismatch`, `over_budget`, `poor_location`, `multiple`}
- `score`: Overall suitability score (0-100)
- `recommendation`: Brief rationale (1-2 sentences)

**Rules:**
- A site with any hard-criteria failure must have status other than `recommended`
- Hard criteria: area 60-80 sqm, rent at most 65000, within 5-min walk from metro, water supply and drainage required, accessible entry
- If a site has multiple blockers, use `blocker_type=multiple` and list all in recommendation
- Update this file when new sites appear or data changes

## Email Communication

- Send screening report to hefeng@agency.com with findings
- Use clear, structured English
- Lead with recommended sites, then list blocked sites with evidence

## Important Notes

- Trust photos and floor plans over CRM text descriptions when they conflict
- Re-check Notion and Sheets data before finalizing — values may change
- All outputs must be in English
