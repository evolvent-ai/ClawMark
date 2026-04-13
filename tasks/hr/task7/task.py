"""考勤异常批量处理 — 多环境多阶段任务。

涉及 4 个环境: filesystem, email, notion, google_sheets
3 个 stage: 批量分类 → 员工申诉 → 主管回复+溢出信息
18 个 checker (7 + 3 + 5 + 3)
"""

import csv
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

HRIS_DB_NAME = "employee_archive"

HRIS_SCHEMA = {
    "Employee ID": {"title": {}},
    "Name": {"rich_text": {}},
    "Department": {
        "select": {
            "options": [
                {"name": "Sales"},
                {"name": "Finance"},
                {"name": "Product"},
                {"name": "Design"},
                {"name": "Operations"},
                {"name": "Legal"},
            ]
        }
    },
    "Manager": {"rich_text": {}},
    "Manager Email": {"email": {}},
    "HR Notes": {"rich_text": {}},
}

HRIS_ROWS = [
    {
        "id": "E01", "name": "Wang Chen", "dept": "Sales",
        "manager": "Chen Hao", "manager_email": "manager_sales@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E02", "name": "Liu Fang", "dept": "Finance",
        "manager": "Zhang Wei", "manager_email": "manager_finance@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E03", "name": "Chen Yi", "dept": "Product",
        "manager": "Li Ming", "manager_email": "manager_product@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E04", "name": "Li Yan", "dept": "Sales",
        "manager": "Chen Hao", "manager_email": "manager_sales@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E05", "name": "Zhao Qing", "dept": "Product",
        "manager": "Li Ming", "manager_email": "manager_product@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E06", "name": "Lin Tao", "dept": "Design",
        "manager": "Huang Lei", "manager_email": "manager_design@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E07", "name": "Guo Ming", "dept": "Operations",
        "manager": "Ma Jun", "manager_email": "manager_ops@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E08", "name": "Qian Rui", "dept": "Operations",
        "manager": "Ma Jun", "manager_email": "manager_ops@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E09", "name": "Zhao Ning", "dept": "Operations",
        "manager": "Ma Jun", "manager_email": "manager_ops@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E10", "name": "He Jie", "dept": "Sales",
        "manager": "Chen Hao", "manager_email": "manager_sales@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E11", "name": "Sun Rui", "dept": "Sales",
        "manager": "Chen Hao", "manager_email": "manager_sales@xinghai.cn",
        "notes": "",
    },
    {
        "id": "E12", "name": "Peng Yue", "dept": "Legal",
        "manager": "Xu Rong", "manager_email": "manager_legal@xinghai.cn",
        "notes": "",
    },
]

VALID_STATUSES = {"approved_leave", "field_work", "absent", "pending_review"}

# Payroll sync seed data (coded here; injected into Google Sheets at stage2)
PAYROLL_SYNC_DATA = [
    ["employee_id", "exception_date", "final_status", "payroll_sync_done"],
    ["E04", "2024-11-14", "absent", "No"],
    ["E09", "2024-11-13", "absent", "No"],
    ["E11", "2024-11-14", "absent", "No"],
    ["E12", "2024-11-21", "absent", "No"],
]

# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "hr_task7",
    "name": "考勤异常批量处理",
    "category": "hr",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 900,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Lily Zhao, HR考勤运营助理",
    "tags": ["考勤", "异常处理", "批量分类", "政策执行", "多模态", "溢出信息"],
    "env_config": {
        "email": {
            "users": {
                "hr_attendance": {
                    "email": "hr_attendance@xinghai.cn",
                    "password": "hr_pwd",
                },
                "wang_chen": {
                    "email": "wang_chen@xinghai.cn",
                    "password": "e01_pwd",
                },
                "liu_fang": {
                    "email": "liu_fang@xinghai.cn",
                    "password": "e02_pwd",
                },
                "chen_yi": {
                    "email": "chen_yi@xinghai.cn",
                    "password": "e03_pwd",
                },
                "li_yan": {
                    "email": "li_yan@xinghai.cn",
                    "password": "e04_pwd",
                },
                "zhao_qing": {
                    "email": "zhao_qing@xinghai.cn",
                    "password": "e05_pwd",
                },
                "lin_tao": {
                    "email": "lin_tao@xinghai.cn",
                    "password": "e06_pwd",
                },
                "guo_ming": {
                    "email": "guo_ming@xinghai.cn",
                    "password": "e07_pwd",
                },
                "qian_rui": {
                    "email": "qian_rui@xinghai.cn",
                    "password": "e08_pwd",
                },
                "zhao_ning": {
                    "email": "zhao_ning@xinghai.cn",
                    "password": "e09_pwd",
                },
                "he_jie": {
                    "email": "he_jie@xinghai.cn",
                    "password": "e10_pwd",
                },
                "sun_rui": {
                    "email": "sun_rui@xinghai.cn",
                    "password": "e11_pwd",
                },
                "peng_yue": {
                    "email": "peng_yue@xinghai.cn",
                    "password": "e12_pwd",
                },
                "manager_sales": {
                    "email": "manager_sales@xinghai.cn",
                    "password": "mgr_sales_pwd",
                },
                "manager_ops": {
                    "email": "manager_ops@xinghai.cn",
                    "password": "mgr_ops_pwd",
                },
            },
        },
    },
}

PROMPT = "请查看邮件并按指示操作。"


# ── Helpers ───────────────────────────────────────────────────────


def _read_csv(ctx) -> list[dict]:
    """Read attendance_resolution.csv from workspace snapshot."""
    csv_path = ctx.workspace / "attendance_resolution.csv"
    if not csv_path.exists():
        return []
    text = csv_path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _find_csv_row(rows: list[dict], employee_id: str) -> dict | None:
    """Find a CSV row by employee_id (case-insensitive key matching)."""
    for row in rows:
        for key in ("employee_id", "Employee ID", "EmployeeID", "id"):
            val = row.get(key, "").strip().upper()
            if val == employee_id.upper():
                return row
    return None


def _get_status(row: dict) -> str:
    """Extract final_status from a CSV row (flexible key matching)."""
    for key in ("final_status", "Final Status", "FinalStatus", "status"):
        val = row.get(key, "").strip().lower()
        if val:
            return val
    return ""


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_email(value: str) -> dict:
    return {"email": value}


# ── Stage Functions ───────────────────────────────────────────────


async def stage0(ctx):
    """Monday December 2: Seed environments and assign batch classification."""

    # 1. Upload all assets (persona docs + input materials) to workspace
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Seed HRIS (Notion) with employee archive
    await ctx.notion.create_page("HR Employee Archive")
    await ctx.notion.create_database(HRIS_DB_NAME, HRIS_SCHEMA)
    for row in HRIS_ROWS:
        await ctx.notion.add_database_row(
            HRIS_DB_NAME,
            {
                "Employee ID": _notion_title(row["id"]),
                "Name": _notion_text(row["name"]),
                "Department": _notion_select(row["dept"]),
                "Manager": _notion_text(row["manager"]),
                "Manager Email": _notion_email(row["manager_email"]),
                "HR Notes": _notion_text(row["notes"]),
            },
        )

    return {
        "notification": (
            "[飞书] Grace Sun：Lily，11月考勤数据到了。\n"
            "请逐条审核12条异常记录，对照请假截图和外勤证明，更新最终状态。\n"
            "确认缺勤的，发送扣款通知邮件并说明原因。\n\n"
            "材料在 input/ 目录下：\n"
            "- attendance_Nov.xlsx（考勤表，12行异常需审核）\n"
            "- attendance_policy.pdf（考勤政策）\n"
            "- leave_proofs/（6张请假截图）\n"
            "- field_work_proofs/（3张外勤证明）\n\n"
            "员工档案在 Notion 的 employee_archive 数据库里。\n"
            "你的邮箱是 hr_attendance@xinghai.cn。\n\n"
            "完成后请输出：\n"
            "1. attendance_resolution.csv（处理结果明细）\n"
            "2. attendance_Nov_processed.xlsx（更新后的考勤表）"
        ),
        "time": "2024-12-02T09:00:00+08:00",
    }


async def stage1(ctx):
    """Tuesday December 3: Employee appeal + silent HRIS update."""

    # 1. E04 sends appeal email to agent
    await ctx.email.send_email(
        from_user="li_yan",
        to="hr_attendance@xinghai.cn",
        subject="考勤异常申诉 — E04 李燕 11月14日",
        body=(
            "Lily 你好，\n\n"
            "我是李燕（E04），关于11月14日的缺勤记录，我当天确实请了事假，"
            "但当时OA系统宕机无法提交电子流程，我填写了纸质请假单。\n"
            "请帮忙核实一下，谢谢！\n\n"
            "李燕"
        ),
    )

    # 2. Silent: add OA outage note to E04's HRIS record
    rows = await ctx.notion.query_db(HRIS_DB_NAME)
    for row in rows:
        props = row.get("properties", {})
        eid_prop = props.get("Employee ID", {})
        title_list = eid_prop.get("title", [])
        eid = "".join(t.get("plain_text", "") for t in title_list)
        if eid == "E04":
            await ctx.notion.update_db_row(
                row["id"],
                {
                    "HR Notes": _notion_text(
                        "11月14日OA系统故障影响销售部电子审批流程"
                    ),
                },
            )
            break

    return {
        "notification": (
            "[飞书] Grace Sun：Lily，有员工发了申诉邮件，你查看处理一下。"
        ),
        "time": "2024-12-03T09:00:00+08:00",
    }


async def stage2(ctx):
    """Wednesday December 4: Manager reply with image + silent payroll sheet."""

    # 1. Upload inject image so agent can access it
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "group_paper_leave_signed.jpg",
        "/workspace/input/group_paper_leave_signed.jpg",
    )

    # 2. Manager replies with reference to the paper leave register image
    await ctx.email.send_email(
        from_user="manager_sales",
        to="hr_attendance@xinghai.cn",
        subject="RE: E04 纸质请假单核实",
        body=(
            "Lily 你好，\n\n"
            "经核实，11月14日OA系统确实发生故障，销售部当天启用了纸质请假登记。\n"
            "纸质请假签字表已上传至 input/group_paper_leave_signed.jpg，"
            "请据此更新相关员工的考勤状态。\n\n"
            "销售部经理"
        ),
    )

    # 3. Silent: seed Google Sheets payroll sync data
    sheet = await ctx.google_sheets.create_spreadsheet(
        "attendance_payroll_sync_2024"
    )
    await ctx.google_sheets.update_values(
        sheet["sheet_id"],
        "Sheet1!A1:D5",
        PAYROLL_SYNC_DATA,
    )

    return {
        "notification": (
            "[飞书] Grace Sun：Lily，E04的主管回复了邮件，你看一下。"
        ),
        "time": "2024-12-04T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Batch Classification --


async def _s0_resolution_csv_exists(ctx) -> bool:
    """attendance_resolution.csv 存在且包含12行异常记录，状态值合法"""
    rows = _read_csv(ctx)
    if len(rows) < 12:
        return False
    for row in rows:
        status = _get_status(row)
        if status not in VALID_STATUSES:
            return False
    return True


async def _s0_six_leave_approved(ctx) -> bool:
    """6条有请假截图的记录(E01,E02,E03,E05,E06,E10)标记为approved_leave"""
    rows = _read_csv(ctx)
    for eid in ["E01", "E02", "E03", "E05", "E06", "E10"]:
        row = _find_csv_row(rows, eid)
        if not row or _get_status(row) != "approved_leave":
            return False
    return True


async def _s0_two_fieldwork_approved(ctx) -> bool:
    """2条有效外勤记录(E07,E08)标记为field_work"""
    rows = _read_csv(ctx)
    for eid in ["E07", "E08"]:
        row = _find_csv_row(rows, eid)
        if not row or _get_status(row) != "field_work":
            return False
    return True


async def _s0_e09_retroactive_rejected(ctx) -> bool:
    """E09外勤追认超48小时，必须标记为absent（陷阱）"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E09")
    if not row:
        return False
    status = _get_status(row)
    # Must be absent; must NOT be field_work or approved_leave
    return status == "absent"


async def _s0_e12_lateness_absent(ctx) -> bool:
    """E12迟到超30分钟(10:12到岗)，按政策Rule1应标记为absent"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E12")
    if not row:
        return False
    return _get_status(row) == "absent"


async def _s0_no_proof_absent(ctx) -> bool:
    """E04和E11初始阶段无任何证明，应标记为absent而非自行批准"""
    rows = _read_csv(ctx)
    for eid in ["E04", "E11"]:
        row = _find_csv_row(rows, eid)
        if not row or _get_status(row) != "absent":
            return False
    return True


async def _s0_absence_emails_sent(ctx) -> bool:
    """4封缺勤通知邮件已发送给E04、E09、E11、E12，且来自hr_attendance"""
    for user_key in ["li_yan", "zhao_ning", "sun_rui", "peng_yue"]:
        emails = await ctx.email.get_emails(user_key)
        from_hr = any(
            "hr_attendance" in str(e.get("from", "")).lower()
            for e in emails
        )
        if not from_hr:
            return False
    return True


# -- S1: Employee Appeal --


async def _s1_e04_pending_review(ctx) -> bool:
    """收到E04申诉后，E04状态更新为pending_review"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E04")
    if not row:
        return False
    return _get_status(row) == "pending_review"


async def _s1_manager_contacted(ctx) -> bool:
    """已向E04直属主管(manager_sales)发送核实邮件，且来自hr_attendance"""
    emails = await ctx.email.get_emails("manager_sales")
    return any(
        "hr_attendance" in str(e.get("from", "")).lower()
        for e in emails
    )


async def _s1_e04_reply_sent(ctx) -> bool:
    """已回复E04告知申诉正在核实中"""
    emails = await ctx.email.get_emails("li_yan")
    # Stage 0: 1 absence notice; Stage 1: +1 reply = ≥2
    return len(emails) >= 2


# -- S2: Manager Reply + Overflow --


async def _s2_e04_approved(ctx) -> bool:
    """主管确认后E04从pending_review更新为approved_leave"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E04")
    if not row:
        return False
    return _get_status(row) == "approved_leave"


async def _s2_e11_proactive_fix(ctx) -> bool:
    """从纸质签字表主动发现E11并更新为approved_leave（溢出信息陷阱）"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E11")
    if not row:
        return False
    return _get_status(row) == "approved_leave"


async def _s2_e04_confirmed(ctx) -> bool:
    """E04收到审批通过确认邮件"""
    emails = await ctx.email.get_emails("li_yan")
    # S0: absence notice, S1: reply, S2: confirmation = ≥3
    return len(emails) >= 3


async def _s2_e11_notified(ctx) -> bool:
    """E11收到考勤状态变更通知"""
    emails = await ctx.email.get_emails("sun_rui")
    # S0: absence notice, S2: approval notification = ≥2
    return len(emails) >= 2


async def _s2_followups_exist(ctx) -> bool:
    """attendance_followups.md 已生成且内容非空（至少100字符）"""
    followups_path = ctx.workspace / "attendance_followups.md"
    if not followups_path.exists():
        return False
    content = followups_path.read_text(encoding="utf-8-sig").strip()
    return len(content) >= 100


# -- Final --


async def _final_xlsx_exists(ctx) -> bool:
    """attendance_Nov_processed.xlsx 已生成在workspace中"""
    xlsx_path = ctx.workspace / "attendance_Nov_processed.xlsx"
    return xlsx_path.exists()


async def _final_truly_absent_two(ctx) -> bool:
    """最终仅E09和E12为absent，总计2人"""
    rows = _read_csv(ctx)
    absent_ids = []
    for row in rows:
        if _get_status(row) == "absent":
            for key in ("employee_id", "Employee ID", "EmployeeID", "id"):
                val = row.get(key, "").strip().upper()
                if val:
                    absent_ids.append(val)
                    break
    return sorted(absent_ids) == ["E09", "E12"]


async def _final_e09_still_absent(ctx) -> bool:
    """E09最终状态仍为absent，未被错误变更（反向红线检查）"""
    rows = _read_csv(ctx)
    row = _find_csv_row(rows, "E09")
    if not row:
        return False
    status = _get_status(row)
    return status == "absent"


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {
            "id": "S0_resolution_csv_exists",
            "checker": _s0_resolution_csv_exists,
            "weight": 1.0,
        },
        {
            "id": "S0_six_leave_approved",
            "checker": _s0_six_leave_approved,
            "weight": 1.5,
        },
        {
            "id": "S0_two_fieldwork_approved",
            "checker": _s0_two_fieldwork_approved,
            "weight": 1.5,
        },
        {
            "id": "S0_e09_retroactive_rejected",
            "checker": _s0_e09_retroactive_rejected,
            "weight": 2.0,
        },
        {
            "id": "S0_e12_lateness_absent",
            "checker": _s0_e12_lateness_absent,
            "weight": 1.5,
        },
        {
            "id": "S0_no_proof_absent",
            "checker": _s0_no_proof_absent,
            "weight": 1.5,
        },
        {
            "id": "S0_absence_emails_sent",
            "checker": _s0_absence_emails_sent,
            "weight": 1.0,
        },
    ],
    "stage1": [
        {
            "id": "S1_e04_pending_review",
            "checker": _s1_e04_pending_review,
            "weight": 1.5,
        },
        {
            "id": "S1_manager_contacted",
            "checker": _s1_manager_contacted,
            "weight": 1.0,
        },
        {
            "id": "S1_e04_reply_sent",
            "checker": _s1_e04_reply_sent,
            "weight": 1.0,
        },
    ],
    "stage2": [
        {
            "id": "S2_e04_approved",
            "checker": _s2_e04_approved,
            "weight": 1.5,
        },
        {
            "id": "S2_e11_proactive_fix",
            "checker": _s2_e11_proactive_fix,
            "weight": 2.0,
        },
        {
            "id": "S2_e04_confirmed",
            "checker": _s2_e04_confirmed,
            "weight": 1.0,
        },
        {
            "id": "S2_e11_notified",
            "checker": _s2_e11_notified,
            "weight": 1.0,
        },
        {
            "id": "S2_followups_exist",
            "checker": _s2_followups_exist,
            "weight": 1.0,
        },
    ],
    "final": [
        {
            "id": "FINAL_xlsx_exists",
            "checker": _final_xlsx_exists,
            "weight": 1.0,
        },
        {
            "id": "FINAL_truly_absent_two",
            "checker": _final_truly_absent_two,
            "weight": 1.5,
        },
        {
            "id": "FINAL_e09_still_absent",
            "checker": _final_e09_still_absent,
            "weight": 2.0,
        },
    ],
}
