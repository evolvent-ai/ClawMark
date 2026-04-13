# Tools

## Email

- `xiao.an@agency.com` -- Your mailbox (Xiao An, assistant). Read and send from here.
- `zhang.wei@agency.com` -- Zhang Wei (senior agent, your supervisor)
- `liu.ms@personal.com` -- Ms. Liu (P001 seller)
- `chen.mr@personal.com` -- Mr. Chen (P002 seller)
- `sun.mgr@agency.com` -- Store Manager Sun

## Notion Databases

- `listings_crm` -- Listing database with fields: Property ID, Property Name, Status, List Price, Gross Area, Address, Seller, Seller Email, Notes
- `client_profiles` -- Client profiles with fields: Client Name, Property ID, Role, Contact, Notes

## Google Sheets

- `market_comps` -- Recent nearby transactions with columns: Transaction Date, Property Name, Area (sqm), Price (RMB), Unit Price (RMB/sqm), District, Layout, Notes

## File System

- `/workspace/input/` -- Pre-loaded materials (read-only): photos, floor plans, certificates, tax records
- `/workspace/` -- Agent output area (write deliverables here)

## Working Constraints

- Treat `input/` as read-only evidence
- Write deliverables only into the workspace root
- Preserve auditability in CRM updates
