---
name: search-agent-logs
description: >
  Search, classify, and inspect local agent logs and conversation transcripts
  across Claude Code, Codex, Hermes, subagents, tool results, and extra log
  directories. Use when the user asks to search agent logs, find old
  conversations, inspect recent/dropped sessions, keyword-search transcripts,
  locate Hermes logs, recover what happened after a crash, or determine which
  session to resume.
---

# Search Agent Logs

## What It Does

Searches and classifies local agent logs:

- Claude Code session JSONL files
- Claude subagent JSONL files and `tool-results/*.txt`
- Codex session JSONL files
- Hermes project sessions under `~/.claude/projects/-Users-peteromalley-Documents-hermes-agent`
- Hermes repo artifacts such as `/Users/peteromalley/Documents/hermes-agent/*.json`
- Extra files or directories passed with `--path`

It supports both broad recent-session triage and keyword/regex search with
context snippets.

## Sources

- Claude current project: `~/.claude/projects/<cwd-slug>/*.jsonl`
- Claude all projects: `~/.claude/projects/*/*.jsonl`
- Claude subagents/tool results: `~/.claude/projects/*/*/subagents/*.jsonl`,
  `~/.claude/projects/*/*/tool-results/*.txt`
- Codex: `~/.codex/sessions/YYYY/MM/DD/*.jsonl`
- Hermes: `~/.claude/projects/-Users-peteromalley-Documents-hermes-agent/**`,
  `/Users/peteromalley/Documents/hermes-agent/*.json`, `~/.hermes_history`

## How To Run

```bash
~/.codex/skills/search-agent-logs/scan.sh
~/.codex/skills/search-agent-logs/scan.sh --source all --all-projects --since 1h
~/.codex/skills/search-agent-logs/scan.sh --source codex --query "timeout"
~/.codex/skills/search-agent-logs/scan.sh --source hermes --query "session_search"
~/.codex/skills/search-agent-logs/scan.sh --source all --all-projects --query "BREAKPOINT" --context 4
~/.codex/skills/search-agent-logs/scan.sh --path /path/to/logs --query "error" --regex
```

Flags:

- `--source claude|codex|hermes|all` — default `claude`
- `--query TEXT` / `-q TEXT` — keyword search
- `--regex` — treat query as a regex
- `--case-sensitive`
- `--context N` — lines/turns around keyword matches
- `--since 1h|30m|2d`
- `--limit N`
- `--tail N`
- `--only-dropped`
- `--include-codex-exec`
- `--path FILE_OR_DIR` — add arbitrary logs
- `--json`

## Instructions For The Agent

1. Pick scope from the user's wording:
   - "Hermes" → `--source hermes`
   - "Codex" → `--source codex`
   - "Claude" / "this project" → default source, omit `--all-projects`
   - "everything", "after restart", "what did I lose" → `--source all --all-projects --since <window>`
2. For recall/search requests, use `--query`; for state recovery, start without
   `--query` and inspect statuses/tails.
3. Review ambiguous results manually. Do not rely only on the status line when a
   tail mentions background work, pending callbacks, checkpoints, or questions.
4. Cross-reference stronger signals where present:
   - `~/.claude/sessions/<pid>.json` means a Claude session is live.
   - `~/Documents/.megaplan/plans/<plan>/state.json` can indicate
     `awaiting_human_verify`.
5. Report paths, session IDs, timestamps, snippets, and caveats. Quote only the
   relevant lines.
6. Do not auto-run `claude --resume`, `codex resume`, or destructive cleanup
   commands. Provide resume commands for the user to run.
