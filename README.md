# search-agent-logs

Agent skill for searching and triaging local Claude Code, Codex, and Hermes
session logs.

## Install

Copy and paste this prompt into your coding agent:

```text
Install the search-agent-logs skill from https://github.com/peteromallet/search-agent-logs. Install it for every agent system you can detect: copy the repo to ~/.codex/skills/search-agent-logs for Codex, copy it to ~/.claude/skills/search-agent-logs for Claude Code, and for agents that use AGENTS.md or another repo/root instruction file, convert SKILL.md into an AGENTS.md-compatible instruction block and tell me where you put it. Then verify the install by running the skill's scan.sh smoke test with --source all --since 1h --limit 3.
```

Or run this shell command yourself:

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
