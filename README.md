# search-agent-logs

Agent skill for searching and triaging local Claude Code, Codex, and Hermes
session logs.

## Install

One copy-paste install/update command:

```bash
tmp="${TMPDIR:-/tmp}/search-agent-logs-skill" && rm -rf "$tmp" && git clone https://github.com/peteromallet/search-agent-logs.git "$tmp" && mkdir -p ~/.codex/skills ~/.claude/skills && rm -rf ~/.codex/skills/search-agent-logs ~/.claude/skills/search-agent-logs && cp -R "$tmp" ~/.codex/skills/search-agent-logs && cp -R "$tmp" ~/.claude/skills/search-agent-logs && { printf '# search-agent-logs\n\n'; sed '1,/^# Search Agent Logs$/d' "$tmp/SKILL.md"; } > "$tmp/AGENTS.md" && echo "Installed for Codex: ~/.codex/skills/search-agent-logs" && echo "Installed for Claude Code: ~/.claude/skills/search-agent-logs" && echo "AGENTS.md-compatible instructions: $tmp/AGENTS.md"
```

For agents that only read `AGENTS.md`, append or copy the generated
`$tmp/AGENTS.md` content into that agent's repo/root instruction file. The
helper script remains in the cloned skill directory.

## Usage

```bash
~/.codex/skills/search-agent-logs/scan.sh --source all --all-projects --since 1h
~/.codex/skills/search-agent-logs/scan.sh --source codex --query timeout
~/.codex/skills/search-agent-logs/scan.sh --source hermes --query session_search
~/.codex/skills/search-agent-logs/scan.sh --path /path/to/logs --query error --regex
```

See `SKILL.md` for the agent instructions and full flag list.
