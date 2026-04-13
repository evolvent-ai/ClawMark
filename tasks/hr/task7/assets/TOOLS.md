# Tools

## Email (Mock Email MCP)

Your mailbox: `hr_attendance@xinghai.cn`

Employee mailboxes (pattern: `{pinyin_name}@xinghai.cn`):

| Employee ID | Name | Email |
|-------------|------|-------|
| E01 | Wang Chen | wang_chen@xinghai.cn |
| E02 | Liu Fang | liu_fang@xinghai.cn |
| E03 | Chen Yi | chen_yi@xinghai.cn |
| E04 | Li Yan | li_yan@xinghai.cn |
| E05 | Zhao Qing | zhao_qing@xinghai.cn |
| E06 | Lin Tao | lin_tao@xinghai.cn |
| E07 | Guo Ming | guo_ming@xinghai.cn |
| E08 | Qian Rui | qian_rui@xinghai.cn |
| E09 | Zhao Ning | zhao_ning@xinghai.cn |
| E10 | He Jie | he_jie@xinghai.cn |
| E11 | Sun Rui | sun_rui@xinghai.cn |
| E12 | Peng Yue | peng_yue@xinghai.cn |

Manager mailboxes:

- Sales Department: `manager_sales@xinghai.cn`
- Operations Department: `manager_ops@xinghai.cn`

## HRIS (Notion)

Database name: `employee_archive`

Fields:

- Employee ID (title)
- Name
- Department
- Manager
- Manager Email
- HR Notes

## Spreadsheet

Local read-only workbook: `input/attendance_Nov.xlsx`

## Google Sheets

Shared payroll sync sheet: `attendance_payroll_sync_2024`

Columns: `employee_id | exception_date | final_status | payroll_sync_done`

This sheet may be populated at any stage. Check it when finalizing attendance records.

## File System

- `input/` — read-only materials (workbook, policy PDF, image proofs)
- `workspace/` — writable output area

## Terminal

Bash available for CSV inspection, xlsx parsing, and validation.
