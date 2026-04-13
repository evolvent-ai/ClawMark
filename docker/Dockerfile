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

# Install OpenClaw CLI
RUN npm install -g openclaw@2026.3.31 && openclaw --version

# Install uv for uvx (MCP server execution)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Python libraries used by skills (calendar, sheets, etc.)
RUN pip3 install caldav openai-whisper pymupdf

RUN mkdir -p /workspace /logs /root/.openclaw
WORKDIR /workspace

CMD ["sleep", "infinity"]
