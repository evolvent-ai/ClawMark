---
name: notion
description: "Read and update Notion databases and pages via mcporter + Notion MCP server"
---

# Notion Skill

Use `mcporter` to access Notion through the official Notion MCP server.
ClawMark's default container image preinstalls both `mcporter` and
`@notionhq/notion-mcp-server`. If you are on a custom image and either command
is missing, install them first.

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

Do **not** pass a raw JSON blob as the second positional argument, e.g.
`mcporter call notion.<tool_name> '{"field":"value"}'`. For Notion tools this
often gets treated as a string instead of an object body.

Common Notion examples:

```bash
# Search for pages/databases by title
mcporter call notion.API-post-search query=content_calendar

# Same call using function-call syntax
mcporter call 'notion.API-post-search(query: "content_calendar")'
```

Database ID and other task-specific details will be provided in the task
context.
