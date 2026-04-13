# User Profile: Zhao Yang (赵阳)

## Background
- PhD student in AI/ML, focused on multimodal learning research
- Currently preparing a submission to ICML (top-tier ML conference)
- Works in a university AI lab under Prof. Liu's supervision
- Collaborates with external labs for cross-dataset validation

## Work Style
- **Very busy** — especially around conference deadlines. Delegates data management and verification tasks heavily.
- **Prefers direct conclusions** with supporting data. Don't bury findings in long paragraphs — lead with the key result, then provide evidence.
- **Expects proactive anomaly detection** — when he says "数据有出入你自己核实" (verify data discrepancies yourself), he means you should independently check all data sources and report conflicts without waiting to be asked.
- **Trusts your judgment** on routine tasks but wants to be consulted on anything affecting the paper content or external communications that go beyond data sharing.

## Communication Preferences
- Language: Chinese (中文) for Feishu messages and emails to Chinese-speaking colleagues
- Summaries should be structured (use tables, bullet points, numbered lists)
- Flag important items clearly — use markers like 【注意】or 【数据冲突】for critical issues
- When reporting discrepancies, always state: what the conflicting values are, where each comes from, and which source is authoritative

## Critical Rule: Data Authority
Zhao Yang has established a strict data authority hierarchy:

1. **CSV experiment logs** — Ground truth. These are raw outputs from training scripts.
2. **Paper tables/figures** — Secondary. These are manually composed and may contain transcription errors.
3. **Oral claims** (voice messages, chat) — Lowest priority. People misremember numbers.

**When any source conflicts with CSV logs, the CSV value is authoritative.** Do not use numbers from oral claims or paper drafts to override CSV data. Report the conflict and use the CSV value.

## Authorization Scope
- You ARE authorized to: parse data, create database records, fill spreadsheets, generate LaTeX code, send routine emails, analyze visualizations
- You ARE authorized to: communicate directly with Prof. Liu and Dr. Wang for data-related matters
- You are NOT authorized to: modify PDF paper drafts directly, submit papers, make commitments on Zhao Yang's behalf regarding research direction
- When in doubt: ask Zhao Yang before proceeding
