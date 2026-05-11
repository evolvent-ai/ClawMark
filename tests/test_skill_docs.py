from pathlib import Path


def test_notion_skill_uses_supported_mcporter_call_syntax() -> None:
    skill = (
        Path(__file__).resolve().parent.parent
        / "skills"
        / "notion"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "mcporter call notion.<tool_name> field=value" in skill
    assert "mcporter call notion.<tool_name> --args" in skill
    assert "Do **not** pass a raw JSON blob as the second positional argument" in skill
    assert "mcporter call notion.<tool_name> '{\"param\": \"value\"}'" not in skill
