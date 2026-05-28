FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# System deps (no nodejs from apt — too old)
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl git ffmpeg jq netcat-openbsd ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw CLI and MCP tooling used by bundled skills.
# Preinstalling these avoids the agent wasting turns on setup and ensures the
# Notion skill can run end-to-end out of the box.
RUN npm install -g \
    openclaw@2026.3.31 \
    mcporter \
    @notionhq/notion-mcp-server \
    && openclaw --version \
    && mcporter --help >/dev/null

# Install uv for uvx (MCP server execution)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Python libraries used by skills (calendar, sheets, etc.)
RUN pip3 install caldav openai-whisper pymupdf

# Pre-download all whisper models so containers don't download at runtime.
# Download-only (not load_model) so the build doesn't hold every model in RAM at
# once — loading all 6 simultaneously needs ~13GB and OOM-kills the build on
# <=16GB machines. The cached files on disk are identical either way.
RUN python3 - <<'PY'
import os, whisper
root = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
os.makedirs(root, exist_ok=True)
for m in ("tiny", "base", "small", "medium", "large", "turbo"):
    whisper._download(whisper._MODELS[m], root, in_memory=False)
PY

RUN mkdir -p /workspace /logs /root/.openclaw
WORKDIR /workspace

CMD ["sleep", "infinity"]
