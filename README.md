# search-agent-logs

Agent skill for searching and triaging local Claude Code, Codex, and Hermes
session logs.

## Install

For Codex:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/peteromallet/search-agent-logs.git ~/.codex/skills/search-agent-logs
```

For Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/peteromallet/search-agent-logs.git ~/.claude/skills/search-agent-logs
```

## Usage

```bash
~/.codex/skills/search-agent-logs/scan.sh --source all --all-projects --since 1h
~/.codex/skills/search-agent-logs/scan.sh --source codex --query timeout
~/.codex/skills/search-agent-logs/scan.sh --source hermes --query session_search
~/.codex/skills/search-agent-logs/scan.sh --path /path/to/logs --query error --regex
```

See `SKILL.md` for the agent instructions and full flag list.
