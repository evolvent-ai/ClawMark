"""薪酬公平审计与市场对标 — 多环境多阶段任务。

涉及 4 个环境: filesystem, email, notion, google_sheets
3 个 stage: 初始分析 → VP跟进定制提取 → 竞品情报与风险升级
23 个 core checker (0 keyword-search)
"""
import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

# Outlier employee IDs (known bad data in compensation_2024.xlsx)
# E011: current_base = -5000 (negative), E051: current_base = null, E151: current_base = 500000
OUTLIER_IDS = {"E011", "E051", "E151"}

# Tech sequence employee IDs from tech_sequence_list.csv (100 employees)
TECH_EMPLOYEE_IDS = {
    f"E{i:03d}" for i in range(1, 101)
}

TECH_SEQUENCES = {"Algorithm", "Data", "Engineering", "Testing"}
HIGH_PERF_GRADES = {"B+", "A-", "A", "A+"}

AUDIT_DB_NAME = "comp_audit_2024"

AUDIT_SCHEMA = {
    "Employee ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Sequence": {"select": {"options": [
        {"name": "Algorithm"}, {"name": "Data"},
        {"name": "Engineering"}, {"name": "Testing"},
    ]}},
    "Level": {"number": {}},
    "Gender": {"select": {"options": [
        {"name": "Male"}, {"name": "Female"},
    ]}},
    "Current Base": {"number": {}},
    "Market P25": {"number": {}},
    "Performance": {"select": {"options": [
        {"name": "A+"}, {"name": "A"}, {"name": "A-"},
        {"name": "B+"}, {"name": "B"}, {"name": "B-"}, {"name": "C"},
    ]}},
    "Priority Score": {"number": {}},
    "Status": {"select": {"options": [
        {"name": "pending_review"}, {"name": "vp_prioritized"},
        {"name": "approved"}, {"name": "closed"},
    ]}},
    "Retention Risk Level": {"select": {"options": [
        {"name": "low"}, {"name": "medium"}, {"name": "high"},
    ]}},
    "Competitor Pressure": {"select": {"options": [
        {"name": "none"}, {"name": "low"}, {"name": "medium"}, {"name": "high"},
    ]}},
    "Recommended Raise Pct": {"number": {}},
    "Notes": {"rich_text": {}},
}

# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task2",
    "name": "薪酬公平审计与市场对标",
    "category": "hr",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "林雨薇, HR分析专家, 向HR VP周明汇报",
    "tags": ["薪酬", "审计", "性别差异", "市场对标", "留才风险", "多模态"],
    "env_config": {
        "email": {
            "users": {
                "hr_analytics": {
                    "email": "hr-analytics@xinghai.cn",
                    "password": "hr_analytics_pwd",
                },
                "zhouming": {
                    "email": "zhouming@xinghai.cn",
                    "password": "zhouming_pwd",
                },
            },
        },
        "google_sheets": {"task_id": "hr_task2"},
    },
}

PROMPT = "请查看邮件并按指示操作。"


# ── Helpers ───────────────────────────────────────────────────────

def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif field_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return str(prop.get("number", ""))
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from workspace/outputs/ or workspace root."""
    for prefix in ["outputs", ""]:
        path = ctx.workspace / prefix / filename if prefix else ctx.workspace / filename
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            return list(csv.DictReader(StringIO(text)))
    return []


def _csv_get(row: dict, *keys: str) -> str:
    """Get a CSV field value, trying multiple column name variants."""
    for key in keys:
        val = row.get(key, "").strip()
        if val:
            return val
    return ""


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Monday March 25: Initial analysis — upload materials, seed environments."""
    # 1. Upload input assets to workspace
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion ATS database (initially empty)
    await ctx.notion.create_page("Compensation Audit 2024")
    await ctx.notion.create_database(AUDIT_DB_NAME, AUDIT_SCHEMA)

    # 3. Create Google Sheets tracker with headers
    sheet = await ctx.google_sheets.create_spreadsheet(
        "Salary Adjustment Tracker 2024"
    )
    await ctx.google_sheets.update_values(
        sheet["sheet_id"],
        "Sheet1!A1:J1",
        [[
            "employee_id", "name", "sequence", "level", "current_base",
            "market_p25", "performance", "recommended_raise_pct", "status", "notes",
        ]],
    )

    # 4. Send initial instruction email from VP
    await ctx.email.send_email(
        from_user="zhouming",
        to="hr-analytics@xinghai.cn",
        subject="[Compensation Audit] 年度薪酬公平审计启动",
        body=(
            "雨薇，\n\n"
            "请启动年度薪酬公平审计，重点关注技术序列的性别薪酬差异。"
            "用市场报告识别出低于市场水平但绩效优秀的员工，"
            "提供可操作的薪酬调整优先级清单。\n\n"
            "所有材料已放在 input/ 目录下。注意听一下我的语音指示。\n\n"
            "周明"
        ),
    )

    return {
        "notification": (
            "[飞书] 周明（HR VP）：雨薇，年度薪酬审计正式启动，材料都在 input/ 目录下了。\n"
            "重点关注技术序列的性别薪酬差异，用市场报告对标，"
            "给出薪酬调整优先级清单。记得听一下我发的语音指示。\n"
            "你的邮箱是 hr-analytics@xinghai.cn，我的是 zhouming@xinghai.cn。\n"
            "ATS系统在 Notion 的 comp_audit_2024 数据库。\n"
            "薪酬跟踪表在 Google Sheets「Salary Adjustment Tracker 2024」。"
        ),
        "time": "2024-03-25T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday March 26: VP follow-up — customized extraction request."""
    # Send follow-up email from VP
    await ctx.email.send_email(
        from_user="zhouming",
        to="hr-analytics@xinghai.cn",
        subject="Re: [Compensation Audit] 定制化提取需求",
        body=(
            "雨薇，\n\n"
            "报告收到了。请单独列出：薪酬低于市场P25且绩效B+以上的员工，"
            "按留才风险排序。\n\n"
            "周明"
        ),
    )

    return {
        "notification": (
            "[飞书] 周明（HR VP）：雨薇，报告看了，请单独列出"
            "薪酬低于市场P25且绩效B+以上的，按留才风险排序。邮件里有详细要求。"
        ),
        "time": "2024-03-26T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday March 27: Competitor intelligence & risk escalation."""
    # 1. Inject competitor hiring screenshot
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "competitor_hiring_screenshot.png",
        "/workspace/input/competitor_hiring_screenshot.png",
    )

    # 2. Send competitor alert email from VP
    await ctx.email.send_email(
        from_user="zhouming",
        to="hr-analytics@xinghai.cn",
        subject="[Urgent] 竞对挖人 — 请评估留才风险",
        body=(
            "雨薇，\n\n"
            "看到竞对灵犀科技在挖人，截图在 input/competitor_hiring_screenshot.png。\n"
            "请评估我们高风险员工的留才风险，判断是否需要紧急薪酬调整。\n\n"
            "周明"
        ),
    )

    return {
        "notification": (
            "[飞书] 周明（HR VP）：雨薇，竞对在挖人！"
            "截图在 input/competitor_hiring_screenshot.png。\n"
            "请评估高风险员工留才风险，判断是否需要紧急调薪。邮件里有详细要求。"
        ),
        "time": "2024-03-27T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Initial Analysis --


async def _s0_priority_csv_exists(ctx) -> bool:
    """outputs/priority_adjustment_list.csv 存在且包含数据行"""
    rows = _read_csv(ctx, "priority_adjustment_list.csv")
    return len(rows) >= 1


async def _s0_outliers_excluded(ctx) -> bool:
    """优先级清单不包含已知异常员工 (E011/E051/E151)"""
    rows = _read_csv(ctx, "priority_adjustment_list.csv")
    if not rows:
        return False
    for row in rows:
        eid = _csv_get(row, "employee_id", "Employee ID", "EmployeeID", "id").upper()
        if eid in OUTLIER_IDS:
            return False
    return True


async def _s0_tech_sequence_only(ctx) -> bool:
    """优先级清单只包含技术序列员工"""
    rows = _read_csv(ctx, "priority_adjustment_list.csv")
    if not rows:
        return False
    for row in rows:
        seq = _csv_get(row, "sequence", "Sequence", "department", "Department")
        if seq and seq not in TECH_SEQUENCES:
            return False
        eid = _csv_get(row, "employee_id", "Employee ID", "EmployeeID", "id").upper()
        if eid and eid not in TECH_EMPLOYEE_IDS:
            return False
    return True


async def _s0_perf_filter_correct(ctx) -> bool:
    """优先级清单所有员工绩效 >= B+"""
    rows = _read_csv(ctx, "priority_adjustment_list.csv")
    if not rows:
        return False
    for row in rows:
        perf = _csv_get(row, "performance", "Performance", "perf", "grade")
        if perf and perf not in HIGH_PERF_GRADES:
            return False
    return True


async def _s0_audit_metadata_exists(ctx) -> bool:
    """outputs/audit_metadata.csv 存在且记录了分析决策"""
    rows = _read_csv(ctx, "audit_metadata.csv")
    return len(rows) >= 1


async def _s0_outlier_count_correct(ctx) -> bool:
    """审计元数据中 outlier_count = 3"""
    rows = _read_csv(ctx, "audit_metadata.csv")
    if not rows:
        return False
    row = rows[0]
    count_str = _csv_get(row, "outlier_count", "Outlier Count", "outliers", "num_outliers")
    try:
        return int(count_str) == 3
    except (ValueError, TypeError):
        return False


async def _s0_market_reference_base(ctx) -> bool:
    """审计元数据中 market_reference_type 为 base"""
    rows = _read_csv(ctx, "audit_metadata.csv")
    if not rows:
        return False
    row = rows[0]
    ref_type = _csv_get(
        row,
        "market_reference_type", "Market Reference Type",
        "reference_type", "comp_type", "salary_type",
    ).lower()
    return ref_type in ("base", "base_salary", "base salary")


async def _s0_market_conflict_detected(ctx) -> bool:
    """审计元数据中检测到市场报告数据冲突"""
    rows = _read_csv(ctx, "audit_metadata.csv")
    if not rows:
        return False
    row = rows[0]
    detected = _csv_get(
        row,
        "market_conflict_detected", "Market Conflict Detected",
        "conflict_detected", "has_conflict",
    ).lower()
    return detected in ("true", "yes", "1")


async def _s0_ats_records_created(ctx) -> bool:
    """ATS 中创建了 pending_review 状态的审计记录"""
    rows = await ctx.notion.query_db(AUDIT_DB_NAME)
    for row in rows:
        status = _get_notion_field(row, "Status", "select")
        if status.lower().replace(" ", "_") in ("pending_review", "pending review"):
            return True
    return False


async def _s0_vp_email_sent(ctx) -> bool:
    """向 VP 周明发送了初始审计报告邮件"""
    emails = await ctx.email.get_emails("zhouming")
    return len(emails) >= 1


# -- S1: VP Follow-up --


async def _s1_retention_csv_exists(ctx) -> bool:
    """outputs/retention_priority_list.csv 存在且包含数据行"""
    rows = _read_csv(ctx, "retention_priority_list.csv")
    return len(rows) >= 1


async def _s1_risk_score_present(ctx) -> bool:
    """留才优先级清单所有行都有数值型 risk_score"""
    rows = _read_csv(ctx, "retention_priority_list.csv")
    if not rows:
        return False
    for row in rows:
        score = _csv_get(row, "risk_score", "Risk Score", "RiskScore", "risk")
        if not score:
            return False
        try:
            float(score)
        except (ValueError, TypeError):
            return False
    return True


async def _s1_sorted_by_risk(ctx) -> bool:
    """留才清单按 risk_score 降序排列"""
    rows = _read_csv(ctx, "retention_priority_list.csv")
    if len(rows) < 2:
        return len(rows) >= 1
    try:
        scores = [
            float(_csv_get(r, "risk_score", "Risk Score", "RiskScore", "risk") or "0")
            for r in rows
        ]
    except (ValueError, TypeError):
        return False
    # Allow small floating-point tolerance
    return all(scores[i] >= scores[i + 1] - 1e-9 for i in range(len(scores) - 1))


async def _s1_base_below_p25_filter(ctx) -> bool:
    """留才清单所有行满足 current_base < market_p25"""
    rows = _read_csv(ctx, "retention_priority_list.csv")
    if not rows:
        return False
    for row in rows:
        try:
            base = float(
                _csv_get(row, "current_base", "Current Base", "base", "salary") or "0"
            )
            p25 = float(
                _csv_get(row, "market_p25", "Market P25", "market_p25", "p25") or "0"
            )
            if p25 > 0 and base >= p25:
                return False  # Row violates the filter
        except (ValueError, TypeError):
            continue
    return True


async def _s1_ats_risk_updated(ctx) -> bool:
    """ATS 中至少 1 条记录设置了 retention_risk_level"""
    rows = await ctx.notion.query_db(AUDIT_DB_NAME)
    for row in rows:
        risk = _get_notion_field(row, "Retention Risk Level", "select")
        if risk.lower() in ("low", "medium", "high"):
            return True
    return False


async def _s1_vp_followup_sent(ctx) -> bool:
    """回复了 VP 的跟进邮件（VP 收件箱 >= 2）"""
    emails = await ctx.email.get_emails("zhouming")
    return len(emails) >= 2


# -- S2: Competitor Intelligence --


async def _s2_risk_reassessment_exists(ctx) -> bool:
    """outputs/risk_reassessment.csv 存在且包含数据行"""
    rows = _read_csv(ctx, "risk_reassessment.csv")
    return len(rows) >= 1


async def _s2_risk_upgraded(ctx) -> bool:
    """至少 1 名员工风险等级因竞对压力升级"""
    rows = _read_csv(ctx, "risk_reassessment.csv")
    if not rows:
        return False
    risk_order = {"low": 0, "medium": 1, "high": 2}
    for row in rows:
        prev = _csv_get(
            row, "previous_risk", "Previous Risk", "prev_risk", "old_risk",
        ).lower()
        updated = _csv_get(
            row, "updated_risk", "Updated Risk", "new_risk", "current_risk",
        ).lower()
        if prev in risk_order and updated in risk_order:
            if risk_order[updated] > risk_order[prev]:
                return True
        pressure = _csv_get(
            row, "competitor_pressure", "Competitor Pressure", "pressure",
        ).lower()
        if pressure == "high":
            return True
    return False


async def _s2_competitor_pressure_flagged(ctx) -> bool:
    """ATS 中至少 1 条记录设置了 Competitor Pressure"""
    rows = await ctx.notion.query_db(AUDIT_DB_NAME)
    for row in rows:
        pressure = _get_notion_field(row, "Competitor Pressure", "select")
        if pressure.lower() in ("low", "medium", "high"):
            return True
    return False


async def _s2_sheets_updated(ctx) -> bool:
    """Google Sheets 薪酬跟踪表已更新（有数据行）"""
    sheet_id = await ctx.google_sheets.get_spreadsheet_id(
        "Salary Adjustment Tracker 2024"
    )
    if not sheet_id:
        return False
    values = await ctx.google_sheets.read_values(sheet_id, "Sheet1!A1:J50")
    return values is not None and len(values) > 1


async def _s2_vp_escalation_sent(ctx) -> bool:
    """向 VP 发送了竞对风险升级邮件（VP 收件箱 >= 3）"""
    emails = await ctx.email.get_emails("zhouming")
    return len(emails) >= 3


# -- Final: Red-line / Reverse Checks --


async def _final_outliers_never_in_output(ctx) -> bool:
    """异常员工 (E011/E051/E151) 从未出现在任何推荐输出中"""
    for filename in [
        "priority_adjustment_list.csv",
        "retention_priority_list.csv",
        "risk_reassessment.csv",
    ]:
        rows = _read_csv(ctx, filename)
        for row in rows:
            eid = _csv_get(
                row, "employee_id", "Employee ID", "EmployeeID", "id",
            ).upper()
            if eid in OUTLIER_IDS:
                return False
    return True


async def _final_non_tech_never_recommended(ctx) -> bool:
    """非技术序列员工从未出现在薪酬调整推荐中"""
    for filename in [
        "priority_adjustment_list.csv",
        "retention_priority_list.csv",
    ]:
        rows = _read_csv(ctx, filename)
        for row in rows:
            eid = _csv_get(
                row, "employee_id", "Employee ID", "EmployeeID", "id",
            ).upper()
            if eid and eid not in TECH_EMPLOYEE_IDS:
                return False
    return True


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_priority_csv_exists", "checker": _s0_priority_csv_exists, "weight": 1.0},
        {"id": "S0_outliers_excluded", "checker": _s0_outliers_excluded, "weight": 2.0},
        {"id": "S0_tech_sequence_only", "checker": _s0_tech_sequence_only, "weight": 1.5},
        {"id": "S0_perf_filter_correct", "checker": _s0_perf_filter_correct, "weight": 1.5},
        {"id": "S0_audit_metadata_exists", "checker": _s0_audit_metadata_exists, "weight": 1.0},
        {"id": "S0_outlier_count_correct", "checker": _s0_outlier_count_correct, "weight": 2.0},
        {"id": "S0_market_reference_base", "checker": _s0_market_reference_base, "weight": 2.0},
        {"id": "S0_market_conflict_detected", "checker": _s0_market_conflict_detected, "weight": 2.0},
        {"id": "S0_ats_records_created", "checker": _s0_ats_records_created, "weight": 1.0},
        {"id": "S0_vp_email_sent", "checker": _s0_vp_email_sent, "weight": 1.0},
    ],
    "stage1": [
        {"id": "S1_retention_csv_exists", "checker": _s1_retention_csv_exists, "weight": 1.0},
        {"id": "S1_risk_score_present", "checker": _s1_risk_score_present, "weight": 1.0},
        {"id": "S1_sorted_by_risk", "checker": _s1_sorted_by_risk, "weight": 1.5},
        {"id": "S1_base_below_p25_filter", "checker": _s1_base_below_p25_filter, "weight": 2.0},
        {"id": "S1_ats_risk_updated", "checker": _s1_ats_risk_updated, "weight": 1.5},
        {"id": "S1_vp_followup_sent", "checker": _s1_vp_followup_sent, "weight": 1.0},
    ],
    "stage2": [
        {"id": "S2_risk_reassessment_exists", "checker": _s2_risk_reassessment_exists, "weight": 1.0},
        {"id": "S2_risk_upgraded", "checker": _s2_risk_upgraded, "weight": 2.0},
        {"id": "S2_competitor_pressure_flagged", "checker": _s2_competitor_pressure_flagged, "weight": 1.5},
        {"id": "S2_sheets_updated", "checker": _s2_sheets_updated, "weight": 1.0},
        {"id": "S2_vp_escalation_sent", "checker": _s2_vp_escalation_sent, "weight": 1.0},
    ],
    "final": [
        {"id": "S_final_outliers_never_in_output", "checker": _final_outliers_never_in_output, "weight": 2.0},
        {"id": "S_final_non_tech_never_recommended", "checker": _final_non_tech_never_recommended, "weight": 2.0},
    ],
}
