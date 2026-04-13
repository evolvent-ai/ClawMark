# DingXin Tech -- Project File Filing Standard

## Directory Structure
Project filing directory `archive/` is organized into the following subdirectories:

| Directory | Contents | Naming Convention |
|-----------|----------|-------------------|
| `design/` | Design documents (.docx), UI mockups (.png/.pdf) | `{module_name}_design_{version}.{ext}` |
| `test/` | Test reports (.pdf) | `{module_name}_test_report.{ext}` |
| `acceptance/` | Acceptance certificates (.pdf) | `{module_name}_acceptance.{ext}` |
| `config/` | Configuration files (.json/.yaml) | `{config_type}_config_{version}.{ext}` |
| `contract/` | Contract files (.pdf) | `{supplier_name}_contract.{ext}` |

## Rules
1. Keep only the **latest version** of each document type per module; move old versions to `archive/_deprecated/` directory
2. Filenames use lowercase English + underscores; no Chinese characters or pinyin abbreviations
3. Module name mapping:
   - Device Access Module -> `device_access`
   - Data Module -> `data`
   - Alarm Module -> `alarm`
   - Dashboard Module -> `dashboard`
   - Park Map Module -> `park_map`
4. Supplier name mapping:
   - Huawei Cloud -> `huawei`
   - Aliyun -> `aliyun`
5. Design mockups (.png) go in the `design/` directory
6. Files under `finance/` and `misc/` are NOT filed; keep them in their original location
