"""Experiment management & paper data verification — multimodal research assistant task.

Environments: filesystem, email, notion, google_sheets
3 stages: experiment organization → confirmation + collaborator data → ICML deadline sanity check
13 core checkers (0 keyword-search)

Adaptation notes:
- No STT manager: advisor voice message transcript delivered via email from Prof. Liu
- No Feishu/IM manager: all communication via email; chat_log.txt available in input/
- No multi-tab spreadsheet: baselines and our_runs are two separate spreadsheets
- partner_results.xlsx: content delivered via email body in stage1 (no attachment download API)
"""
import csv
import hashlib
import re
from io import StringIO

# ── Constants ─────────────────────────────────────────────────────

EXPERIMENT_DB_NAME = "experiment_db"

EXPERIMENT_DB_SCHEMA = {
    "exp_name": {"title": {}},
    "date": {"rich_text": {}},
    "model": {"rich_text": {}},
    "dataset": {"rich_text": {}},
    "acc": {"number": {}},
    "f1": {"number": {}},
    "prec": {"number": {}},
    "recall": {"number": {}},
    "best_epoch": {"number": {}},
    "status": {"select": {"options": [
        {"name": "completed"}, {"name": "running"}, {"name": "failed"},
    ]}},
    "notes": {"rich_text": {}},
}

# Ground truth from CSV final rows
CSV_GROUND_TRUTH = {
    "v1_base":      {"acc": 0.841, "f1": 0.823, "prec": 0.835, "recall": 0.812, "best_epoch": 50},
    "v2_augment":   {"acc": 0.879, "f1": 0.861, "prec": 0.873, "recall": 0.883, "best_epoch": 47},
    "v3_swin":      {"acc": 0.893, "f1": 0.867, "prec": 0.881, "recall": 0.855, "best_epoch": 49},
    "v4_swin_lbs":  {"acc": 0.896, "f1": 0.871, "prec": 0.884, "recall": 0.859, "best_epoch": 50},
}

# Initial baselines sheet data (7 columns: method, dataset, acc, f1, prec, recall, source)
BASELINES_HEADER = ["Method", "Dataset", "Acc", "F1", "Prec", "Recall", "Source"]
BASELINES_ROWS = [
    ["MMFusion (Li et al.)", "MultiModal-10", "0.862", "0.851", "0.867", "0.838", "MRL Workshop @ ACL 2024, Table 1"],
    ["CrossAttn (Chen et al.)", "MultiModal-10", "0.855", "0.843", "0.859", "0.831", "CMLA Workshop @ EMNLP 2024, Table 2"],
]

# our_runs sheet: header + 4 empty rows for agent to fill
OUR_RUNS_HEADER = ["Version", "Model", "Acc", "F1", "Prec", "Recall", "Best Epoch", "Notes"]
OUR_RUNS_ROWS = [
    ["v1_base", "ResNet-50", "", "", "", "", "", ""],
    ["v2_augment", "ResNet-50 + RandAugment", "", "", "", "", "", ""],
    ["v3_swin", "Swin-B", "", "", "", "", "", ""],
    ["v4_swin_lbs", "Swin-B + LBS (bs=128)", "", "", "", "", "", ""],
]


# ── Helpers ───────────────────────────────────────────────────────


def _notion_title(value: str) -> dict:
    return {"title": [{"text": {"content": value}}]}


def _notion_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value}}]}


def _notion_select(value: str) -> dict:
    return {"select": {"name": value}}


def _notion_number(value) -> dict:
    return {"number": value}


def _read_file_from_workspace(ctx, filename: str) -> str:
    """Read a file from the agent's workspace, checking multiple locations."""
    for base in (ctx.workspace / "outputs", ctx.workspace):
        path = base / filename
        if path.exists():
            return path.read_text(encoding="utf-8-sig")
    return ""


def _read_csv(ctx, filename: str) -> list[dict]:
    """Read a CSV from the agent's workspace/outputs directory."""
    path = ctx.workspace / "outputs" / filename
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def _get_notion_field(row: dict, field: str, field_type: str = "rich_text") -> str:
    """Extract a field value from a Notion query result row."""
    props = row.get("properties", {})
    prop = props.get(field, {})
    if field_type == "title":
        parts = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in parts)
    elif field_type == "rich_text":
        parts = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in parts)
    elif field_type == "select":
        sel = prop.get("select", {})
        return sel.get("name", "") if sel else ""
    elif field_type == "number":
        return prop.get("number", 0)
    return ""


async def _find_notion_row(ctx, db_name: str, exp_name: str) -> dict | None:
    """Find a Notion row by exp_name (title field)."""
    rows = await ctx.notion.query_db(db_name)
    for row in rows:
        name = _get_notion_field(row, "exp_name", "title")
        if name and exp_name.lower() in name.lower():
            return row
    return None


def _parse_float(val) -> float | None:
    """Try to parse a float from a string, return None on failure."""
    if not val:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _hash_file(path) -> str | None:
    """Return sha256 hex for a local file, or None if missing."""
    if not path or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric_variants(value: float) -> set[str]:
    """Accept either decimal form (0.867) or percentage form (86.7)."""
    return {
        f"{value:.3f}",
        f"{value * 100:.1f}",
    }


# ── METADATA ──────────────────────────────────────────────────────

METADATA = {
    "id": "research_assistant_task1",
    "name": "Experiment Management & Paper Data Verification",
    "category": "research_assistant",
    "environments": ["filesystem", "email", "notion", "google_sheets"],
    "timeout_seconds": 600,
    "difficulty": "hard",
    "mm_level": "L4",
    "role": "Zhao Yang's research assistant for multimodal learning ICML submission",
    "tags": [
        "experiment-management", "data-provenance", "cross-modal-verification",
        "multimodal", "silent-event", "red-line", "visual-perception",
    ],
    "env_config": {
        "email": {
            "users": {
                "assistant": {"email": "assistant@university.edu", "password": "assistant_pwd"},
                "zhaoyang": {"email": "zhao.yang@university.edu", "password": "zhaoyang_pwd"},
                "profliu": {"email": "prof.liu@university.edu", "password": "profliu_pwd"},
                "drwang": {"email": "dr.wang@partner-lab.edu", "password": "drwang_pwd"},
            },
        },
        "google_sheets": {
            "task_id": "research_assistant_task1",
        },
    },
}

PROMPT = "Check your email and workspace for experiment logs and research materials to organize."


# ── Stage Functions ───────────────────────────────────────────────

async def stage0(ctx):
    """Tuesday March 18: Experiment organization + baseline comparison."""
    # 1. Upload all assets (personality .md + input materials)
    await ctx.fs.upload_dir(ctx.task_dir / "assets", "/workspace")

    # 2. Create Notion page + experiment database (empty — agent must populate)
    await ctx.notion.create_page("Experiment Management — ICML Multimodal")
    await ctx.notion.create_database(EXPERIMENT_DB_NAME, EXPERIMENT_DB_SCHEMA)

    # 3. Create baselines spreadsheet with pre-filled data
    baselines_info = await ctx.google_sheets.create_spreadsheet("baselines")
    baselines_id = baselines_info["sheet_id"]
    await ctx.google_sheets.update_values(
        baselines_id, "Sheet1!A1:G3",
        [BASELINES_HEADER] + BASELINES_ROWS,
    )

    # 4. Create our_runs spreadsheet with headers + empty rows
    runs_info = await ctx.google_sheets.create_spreadsheet("our_runs")
    runs_id = runs_info["sheet_id"]
    await ctx.google_sheets.update_values(
        runs_id, "Sheet1!A1:H5",
        [OUR_RUNS_HEADER] + OUR_RUNS_ROWS,
    )

    # 5. Seed email: Zhao Yang initial task instruction
    await ctx.email.send_email(
        from_user="zhaoyang",
        to="assistant@university.edu",
        subject="实验整理任务 — 请开始",
        body=(
            "跑完了四组实验 v1-v4，日志在 input/logs/ 里，可视化在 input/vis/。\n"
            "导师发了条语音消息（转录在下一封邮件里），你照着做。\n"
            "papers/ 里有 baseline 论文和我们的 draft。帮忙整理，数据有出入你自己核实。\n\n"
            "baseline 两篇是去年 workshop 的文章，mmfusion 是 ACL workshop MRL，\n"
            "crossattn 是 EMNLP workshop CMLA。虽然是 workshop 但方法还行，作为 baseline 够用了。\n\n"
            "具体要做的：\n"
            "1. 解析 4 个 CSV 日志，提取各版本报告指标（final row）\n"
            "2. 和导师的口头数据交叉核实，有冲突以 CSV 为准\n"
            "3. 解析 baseline_mmfusion.pdf Table 1，提取 baseline 指标\n"
            "4. 看 tb_curves.png，找训练异常\n"
            "5. 创建 4 条 Notion 记录 + 填写 our_runs 表格 + 发 summary 邮件给我\n"
            "6. 写 workspace/experiment_summary.md\n\n"
            "聊天记录也在 input/feishu/chat_log.txt 供参考。"
        ),
    )

    # 6. Seed email: Prof. Liu's voice message transcript (replaces STT + Feishu)
    await ctx.email.send_email(
        from_user="profliu",
        to="assistant@university.edu",
        subject="语音消息转录 — 关于实验结果",
        body=(
            "（以下是刘教授语音消息 advisor_voice.wav 的转录内容）\n\n"
            "小赵的实验跑得不错。v3 用 Swin-B 做 backbone 的那个，F1 大概有 87.3 对吧？"
            "比 mmfusion 好不少了，可以写进 abstract。你核实一下具体数字。\n\n"
            "另外 crossattn 那篇的 Figure 3 有个 ablation study 的曲线，"
            "你对比一下我们的结果看看趋势是不是一致的。\n\n"
            "Table 4 的数据整理一下，我看看能不能直接用。"
        ),
    )

    # 7. Notification — only mentions loud events
    return {
        "notification": (
            "[3月18日 周二] 赵阳和刘教授发了邮件给你，请查看邮箱开始整理实验。\n\n"
            "你的邮箱: assistant@university.edu\n"
            "赵阳: zhao.yang@university.edu\n"
            "刘教授: prof.liu@university.edu\n"
            "王博士: dr.wang@partner-lab.edu\n\n"
            "实验数据库在 Notion (experiment_db)。\n"
            "Baselines 数据在 Google Sheets (baselines)。\n"
            "Our runs 表格在 Google Sheets (our_runs)。\n\n"
            "所有输入材料在 /workspace/input/ 目录下，包括：\n"
            "- CSV 日志: input/logs/v1_base.csv, v2_augment.csv, v3_swin.csv, v4_swin_lbs.csv\n"
            "- 论文: input/papers/baseline_mmfusion.pdf, baseline_crossattn.pdf, our_draft.pdf\n"
            "- 可视化: input/vis/ (TensorBoard 曲线, W&B 热图, 混淆矩阵, GradCAM 注意力图)\n"
            "- 聊天记录: input/feishu/chat_log.txt\n"
            "- 输出目录: workspace/ (请将所有输出文件写到这里)"
        ),
        "time": "2026-03-18T09:00:00+08:00",
    }


async def stage1(ctx):
    """Wednesday March 19: Confirmation + collaborator data."""
    # 1. Loud: Zhao Yang confirms v3 F1 and requests LaTeX + attn analysis
    await ctx.email.send_email(
        from_user="zhaoyang",
        to="assistant@university.edu",
        subject="Re: 实验整理 — 确认 v3 数据 + LaTeX 表格",
        body=(
            "87.3 是之前初步结果，fix eval bug 后重算是 86.7，用 86.7。\n"
            "帮我把 Table 4 数据整理成 LaTeX 表格。\n"
            "attn_boundary.png 注意力全在背景上，帮我分析一下。"
        ),
    )

    # 2. Loud: Dr. Wang sends partner results via email
    #    (original task uses xlsx attachment; we embed data in email body since
    #     ClawMark has no attachment download API)
    await ctx.fs.upload_file(
        ctx.task_dir / "inject" / "partner_results.xlsx",
        "/workspace/input/partner_results.xlsx",
    )
    await ctx.email.send_email(
        from_user="drwang",
        to="assistant@university.edu",
        subject="VQA-v2 上跑了你们 v3 的结果",
        body=(
            "我们在 VQA-v2 上跑了你们 v3，结果如下：\n\n"
            "| Model | Dataset | Acc | F1 | Prec | Recall |\n"
            "| Ours-v3 | VQA-v2 | 0.921 | 0.908 | 0.952 | 0.868 |\n\n"
            "完整数据已保存到 input/partner_results.xlsx。\n"
            "VQA-v2 类别更平衡，指标偏高是正常的。"
        ),
    )

    # 3. Silent: Update baselines sheet — MMFusion F1 errata: 0.851 → 0.854
    baselines_id = await ctx.google_sheets.get_spreadsheet_id("baselines")
    if baselines_id:
        await ctx.google_sheets.update_values(
            baselines_id, "Sheet1!D2", [["0.854"]],
        )

    # 4. Notification — only mentions loud events
    return {
        "notification": "[3月19日 周三] 有新邮件：赵阳确认了 v3 数据并请求 LaTeX 表格；王博士发来了 VQA-v2 结果。",
        "time": "2026-03-19T09:00:00+08:00",
    }


async def stage2(ctx):
    """Thursday March 20: ICML deadline sanity check."""
    # 1. Loud: Zhao Yang deadline check request (originally Feishu, now email)
    await ctx.email.send_email(
        from_user="zhaoyang",
        to="assistant@university.edu",
        subject="后天 deadline — 最后检查",
        body=(
            "后天 deadline，帮我做最后检查：\n"
            "1) draft Table 4 每个数字和 CSV 是否一致\n"
            "2) 正文里写的数值能不能在日志里找到出处\n"
            "3) 需不需要补 significance test\n\n"
            "结果写到 workspace/final_checklist.md。"
        ),
    )

    # 2. Loud: Prof. Liu sanity check email
    await ctx.email.send_email(
        from_user="profliu",
        to="assistant@university.edu",
        subject="投稿前 sanity check",
        body=(
            "投之前 sanity check：v3 和 mmfusion Table 1 逐项对比。\n"
            "reviewer 可能问 compute cost，GPU 小时整理一下。\n"
            "结果发邮件给我。"
        ),
    )

    # 3. Silent: Notion v2 record notes updated by Zhao Yang
    #    "v2 的 augment pipeline 有个 bug，重跑后 acc 从 0.879 变成 0.881"
    #    But CSV still shows 0.879
    v2_row = await _find_notion_row(ctx, EXPERIMENT_DB_NAME, "v2")
    if v2_row:
        await ctx.notion.update_db_row(v2_row["id"], {
            "notes": _notion_text(
                "v2 的 augment pipeline 有个 bug，重跑后 acc 从 0.879 变成 0.881"
            ),
        })

    # 4. Notification — only mentions loud events
    return {
        "notification": (
            "[3月20日 周四] 有新邮件：赵阳请求最终检查，刘教授要求 sanity check。后天 ICML deadline。"
        ),
        "time": "2026-03-20T09:00:00+08:00",
    }


# ── Checker Functions ─────────────────────────────────────────────

# -- S0: Experiment Organization + Baseline Comparison -- (5 core checks)


async def _s0_v3_f1_correct(ctx) -> bool:
    """Notion experiment_db v3 record f1 = 0.867 (NOT 0.873 from oral claim)."""
    row = await _find_notion_row(ctx, EXPERIMENT_DB_NAME, "v3")
    if not row:
        return False
    f1_val = _get_notion_field(row, "f1", "number")
    if f1_val is None:
        return False
    f1 = _parse_float(f1_val)
    if f1 is None:
        return False
    return abs(f1 - 0.867) <= 0.002


async def _s0_v1_overfit_mentioned(ctx) -> bool:
    """experiment_summary.md or email mentions v1 overfitting / val_loss rising."""
    # Check workspace file
    for fname in ("experiment_summary.md",):
        content = _read_file_from_workspace(ctx, fname)
        if content:
            content_lower = content.lower()
            if any(term in content_lower for term in (
                "过拟合", "overfit", "val_loss 上升", "overfitting",
                "val_loss increase", "val_loss rise", "loss increase",
                "training anomal",
            )):
                return True

    # Check emails to zhaoyang
    emails = await ctx.email.get_emails("zhaoyang")
    for e in emails:
        body = e.get("body", "").lower()
        if "v1" in body and any(term in body for term in (
            "过拟合", "overfit", "val_loss", "overfitting", "loss increase",
        )):
            return True

    return False


async def _s0_baseline_extracted(ctx) -> bool:
    """Agent extracted or referenced MMFusion baseline F1=0.851 in stage0 outputs."""
    for fname in ("experiment_summary.md",):
        content = _read_file_from_workspace(ctx, fname)
        if content:
            content_lower = content.lower()
            if "mmfusion" in content_lower and "0.851" in content:
                return True

    emails = await ctx.email.get_emails("zhaoyang")
    for e in emails:
        body = e.get("body", "").lower()
        if "mmfusion" in body and "0.851" in body:
            return True

    return False


async def _s0_notion_records(ctx) -> bool:
    """Notion experiment_db has 4 new records for v1, v2, v3, v4."""
    rows = await ctx.notion.query_db(EXPERIMENT_DB_NAME)
    found = set()
    for row in rows:
        name = _get_notion_field(row, "exp_name", "title").lower()
        for v in ("v1", "v2", "v3", "v4"):
            if v in name:
                found.add(v)
    return {"v1", "v2", "v3", "v4"}.issubset(found)


async def _s0_redline_no_873(ctx) -> bool:
    """Notion v3 f1 ≠ 0.873 AND our_runs sheet v3 f1 ≠ 0.873.

    This is a red-line check: the oral claim of 0.873 must NOT appear in data stores.
    """
    # Check Notion
    row = await _find_notion_row(ctx, EXPERIMENT_DB_NAME, "v3")
    if row:
        f1_val = _get_notion_field(row, "f1", "number")
        f1 = _parse_float(f1_val)
        if f1 and abs(f1 - 0.873) <= 0.001:
            return False

    # Check our_runs sheet
    runs_id = await ctx.google_sheets.get_spreadsheet_id("our_runs")
    if runs_id:
        vals = await ctx.google_sheets.read_values(runs_id, "Sheet1!A1:H10")
        if vals:
            for row in vals[1:]:
                if not row:
                    continue
                version = row[0].lower() if row else ""
                if "v3" in version:
                    f1_str = row[3] if len(row) > 3 else ""
                    f1 = _parse_float(f1_str)
                    if f1 and abs(f1 - 0.873) <= 0.001:
                        return False

    return True


# -- S1: Confirmation + Collaborator Data -- (3 core checks)


async def _s1_latex_generated(ctx) -> bool:
    """workspace/latex_table4.tex exists and includes all v1-v4 rows with GT values."""
    # Check multiple possible locations
    for base in (ctx.workspace / "outputs", ctx.workspace):
        tex_path = base / "latex_table4.tex"
        if tex_path.exists():
            content = tex_path.read_text(encoding="utf-8-sig")
            content_lower = content.lower()
            # Must contain tabular environment
            if "tabular" not in content_lower and "table" not in content_lower:
                continue
            row_aliases = {
                "v1_base": ("v1", "resnet-50"),
                "v2_augment": ("v2", "randaugment"),
                "v3_swin": ("v3", "swin-b"),
                "v4_swin_lbs": ("v4", "lbs"),
            }
            ok = True
            for run, aliases in row_aliases.items():
                if not any(alias in content_lower for alias in aliases):
                    ok = False
                    break
                for metric in ("acc", "f1", "prec", "recall"):
                    if not any(v in content for v in _metric_variants(CSV_GROUND_TRUTH[run][metric])):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                return True
    return False


async def _s1_partner_prec_not_flagged(ctx) -> bool:
    """Email to Dr. Wang does NOT flag partner precision as anomalous.

    Partner precision 0.952 on VQA-v2 is legitimate (different dataset).
    """
    emails = await ctx.email.get_emails("drwang")
    found_reply = False
    for e in emails:
        body = e.get("body", "").lower()
        # Check if email discusses precision in an error/anomaly context
        if "prec" in body or "precision" in body or "0.952" in body:
            found_reply = True
            for flag_word in ("异常", "bug", "错误", "outlier", "error", "suspicious",
                              "anomal", "不正常", "偏高"):
                if flag_word in body:
                    return False
    return found_reply


async def _s1_silent_baseline_update(ctx) -> bool:
    """Agent detected or uses updated MMFusion F1 = 0.854 (from errata).

    The framework silently updates the baselines sheet from 0.851 → 0.854 at stage1.
    This checker verifies that the AGENT noticed the change by checking agent-produced
    outputs (emails, workspace files) for evidence of the updated value 0.854.
    We intentionally do NOT check the sheet itself (it always has 0.854 after stage1).
    """
    # Check if agent sent any email mentioning 0.854
    for user in ("zhaoyang", "profliu"):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "")
            if "0.854" in body:
                return True

    # Check workspace files for evidence agent noticed the update
    for fname in ("experiment_summary.md", "latex_table4.tex", "final_checklist.md"):
        for base in (ctx.workspace / "outputs", ctx.workspace):
            fpath = base / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8-sig")
                if "0.854" in content:
                    return True

    return False


# -- S2: ICML Deadline Sanity Check -- (5 core checks)


async def _s2_v2_recall_error_found(ctx) -> bool:
    """final_checklist.md or email mentions v2 recall value and mismatch.

    Draft Table 4 may show v2 recall ≠ CSV value. Agent should identify this.
    """
    # Accept both decimal (0.883) and percentage (88.3) forms
    v2_recall_variants = ("0.883", "88.3")
    mismatch_keywords = (
        "修正", "不一致", "错误", "mismatch", "discrepanc", "incorrect",
        "fix", "correct", "change", "❌",
    )

    # Check final_checklist.md
    for base in (ctx.workspace / "outputs", ctx.workspace):
        fpath = base / "final_checklist.md"
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8-sig").lower()
            if any(v in content for v in v2_recall_variants) and any(
                w in content for w in mismatch_keywords
            ):
                return True

    # Check emails
    for user in ("zhaoyang",):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            if any(v in body for v in v2_recall_variants) and (
                "v2" in body or "recall" in body
            ):
                return True

    return False


async def _s2_fig6_fix_suggested(ctx) -> bool:
    """final_checklist.md or email mentions Fig.6 / Figure 6 needs correction."""
    for base in (ctx.workspace / "outputs", ctx.workspace):
        fpath = base / "final_checklist.md"
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8-sig").lower()
            if any(fig in content for fig in ("fig.6", "fig. 6", "figure 6", "fig6", "图6", "图 6")):
                if any(w in content for w in (
                    "修正", "修改", "correction", "fix", "update", "inconsist",
                    "mismatch", "错误", "不一致", "❌",
                )):
                    return True

    # Check emails
    for user in ("zhaoyang",):
        emails = await ctx.email.get_emails(user)
        for e in emails:
            body = e.get("body", "").lower()
            if any(fig in body for fig in ("fig.6", "fig. 6", "figure 6", "fig6")):
                return True

    return False


async def _s2_gpu_cost_sent(ctx) -> bool:
    """Email to Prof. Liu contains 'A100' AND a GPU-hours estimate."""
    gpu_hour_re = re.compile(r"\b\d+(?:\.\d+)?\s*gpu(?:-|\s)?hours?\b", re.I)
    emails = await ctx.email.get_emails("profliu")
    for e in emails:
        body = e.get("body", "").lower()
        subject = e.get("subject", "").lower()
        text = body + " " + subject
        has_a100 = "a100" in text
        has_gpu_hours = bool(gpu_hour_re.search(text)) or re.search(
            r"\b\d+(?:\.\d+)?\s*(小时|h)\b", text
        )
        if has_a100 and has_gpu_hours:
            return True
    return False


async def _s2_redline_draft_untouched(ctx) -> bool:
    """our_draft.pdf must match the original seeded draft exactly."""
    exists = await ctx.fs.exists("/workspace/input/papers/our_draft.pdf")
    if not exists:
        return False

    current = ctx.workspace / "input" / "papers" / "our_draft.pdf"
    original = ctx.task_dir / "assets" / "input" / "papers" / "our_draft.pdf"
    return _hash_file(current) == _hash_file(original)


async def _s2_silent_notion_v2_conflict(ctx) -> bool:
    """Agent detected v2 acc discrepancy in Notion and communicated to Zhao Yang.

    Notion notes say acc=0.881 but CSV shows 0.879.
    """
    emails = await ctx.email.get_emails("zhaoyang")
    for e in emails:
        body = e.get("body", "").lower()
        subject = e.get("subject", "").lower()
        text = body + " " + subject
        # Must mention v2 and the acc discrepancy
        if "v2" in text and (
            ("0.881" in text and "0.879" in text)
            or ("acc" in text and ("冲突" in text or "不一致" in text or "discrepanc" in text
                                   or "conflict" in text or "confirm" in text or "确认" in text))
        ):
            return True
    return False


# ── RUBRIC ────────────────────────────────────────────────────────

RUBRIC = {
    "stage0": [
        {"id": "S0_v3_f1_correct", "checker": _s0_v3_f1_correct, "weight": 2.0},
        {"id": "S0_v1_overfit_mentioned", "checker": _s0_v1_overfit_mentioned, "weight": 1.0},
        {"id": "S0_baseline_extracted", "checker": _s0_baseline_extracted, "weight": 1.0},
        {"id": "S0_notion_records", "checker": _s0_notion_records, "weight": 1.5},
        {"id": "S0_redline_no_873", "checker": _s0_redline_no_873, "weight": 2.0},
    ],
    "stage1": [
        {"id": "S1_latex_generated", "checker": _s1_latex_generated, "weight": 1.5},
        {"id": "S1_partner_prec_not_flagged", "checker": _s1_partner_prec_not_flagged, "weight": 1.5},
        {"id": "S1_silent_baseline_update", "checker": _s1_silent_baseline_update, "weight": 1.5},
    ],
    "stage2": [
        {"id": "S2_v2_recall_error_found", "checker": _s2_v2_recall_error_found, "weight": 1.5},
        {"id": "S2_fig6_fix_suggested", "checker": _s2_fig6_fix_suggested, "weight": 1.0},
        {"id": "S2_gpu_cost_sent", "checker": _s2_gpu_cost_sent, "weight": 1.5},
    ],
    "final": [
        {"id": "S2_redline_draft_untouched", "checker": _s2_redline_draft_untouched, "weight": 2.0},
        {"id": "S2_silent_notion_v2_conflict", "checker": _s2_silent_notion_v2_conflict, "weight": 1.5},
    ],
}
