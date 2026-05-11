---
name: notion
description: "Read and update Notion databases and pages via mcporter + Notion MCP server"
---

# Notion Skill

Use `mcporter` to access Notion through the official Notion MCP server.

## Install

```bash
npm install -g mcporter
npm install -g @notionhq/notion-mcp-server
```

## Configure

```bash
mcporter config add notion --command "npx @notionhq/notion-mcp-server" --env OPENAPI_MCP_HEADERS='{"Authorization":"Bearer '$NOTION_AGENT_KEY'","Notion-Version":"2022-06-28"}'
```

## Usage

```bash
# List available tools
mcporter list notion --schema

# Call a tool with key=value arguments
mcporter call notion.<tool_name> field=value

# Or use function-call syntax
mcporter call 'notion.<tool_name>(field: "value")'

# If a tool needs a JSON object body, use --args
mcporter call notion.<tool_name> --args '{"field":"value"}'
```

Database ID and other task-specific details will be provided in the task context.
