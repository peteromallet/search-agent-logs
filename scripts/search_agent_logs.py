#!/usr/bin/env python3
"""Search and classify local agent logs for Claude, Codex, and Hermes."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


HOME = Path.home()
HERMES_PROJECT_SLUG = "-Users-peteromalley-Documents-hermes-agent"


@dataclass
class Record:
    source: str
    path: Path
    session_id: str
    mtime: float
    cwd: str = ""
    title: str = ""
    status: str = ""
    resume: str = ""
    tail: list[tuple[str, str]] = field(default_factory=list)
    matches: list[tuple[int, str]] = field(default_factory=list)


def parse_since(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.fullmatch(r"(\d+)([smhd]?)", raw.strip())
    if not m:
        raise SystemExit(f"bad --since: {raw} (use Ns/Nm/Nh/Nd)")
    n = int(m.group(1))
    unit = m.group(2) or "s"
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def project_slug(project_dir: str) -> str:
    return project_dir.replace("/", "-")


def mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def is_live_claude_session(session_id: str) -> bool:
    sessions_dir = HOME / ".claude" / "sessions"
    if not sessions_dir.is_dir():
        return False
    for path in sessions_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if data.get("sessionId") != session_id:
            continue
        pid = data.get("pid")
        if not pid:
            continue
        try:
            subprocess.run(["ps", "-p", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    return False


def iter_claude_files(all_projects: bool, project_dir: str) -> Iterable[Path]:
    root = HOME / ".claude" / "projects"
    if all_projects:
        yield from root.glob("*/*.jsonl")
        yield from root.glob("*/*/subagents/*.jsonl")
        yield from root.glob("*/*/tool-results/*.txt")
        return
    slug = project_slug(project_dir)
    base = root / slug
    yield from base.glob("*.jsonl")
    yield from base.glob("*/subagents/*.jsonl")
    yield from base.glob("*/tool-results/*.txt")


def iter_codex_files(include_exec: bool) -> Iterable[Path]:
    del include_exec
    yield from (HOME / ".codex" / "sessions").glob("*/*/*/*.jsonl")


def iter_hermes_files() -> Iterable[Path]:
    claude_root = HOME / ".claude" / "projects" / HERMES_PROJECT_SLUG
    yield from claude_root.glob("*.jsonl")
    yield from claude_root.glob("*/subagents/*.jsonl")
    yield from claude_root.glob("*/tool-results/*.txt")
    repo = HOME / "Documents" / "hermes-agent"
    yield from repo.glob("*.json")
    hist = HOME / ".hermes_history"
    if hist.exists():
        yield hist


def iter_extra_files(paths: list[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from path.rglob("*.jsonl")
            yield from path.rglob("*.log")
            yield from path.rglob("*.txt")
            yield from path.rglob("*.json")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def compact_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return " ".join(parts)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def claude_text_rows(path: Path) -> list[tuple[str, str]]:
    out = []
    for row in read_jsonl(path):
        typ = row.get("type")
        if typ == "summary":
            out.append(("SUMMARY", compact_text(row.get("summary"))))
        elif typ == "user":
            out.append(("USER", compact_text((row.get("message") or {}).get("content"))))
        elif typ == "assistant":
            msg = row.get("message") or {}
            content = msg.get("content")
            if isinstance(content, list):
                pieces = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            pieces.append(item.get("text") or "")
                        elif item.get("type") == "tool_use":
                            pieces.append(f"[tool_use:{item.get('name','?')}]")
                out.append(("CLAUDE", " ".join(pieces)))
            else:
                out.append(("CLAUDE", compact_text(content)))
    return [(role, text) for role, text in out if text.strip()]


def codex_text_rows(path: Path) -> tuple[list[tuple[str, str]], dict]:
    meta = {}
    out = []
    for row in read_jsonl(path):
        if row.get("type") == "session_meta":
            meta = row.get("payload") or {}
            continue
        if row.get("type") != "response_item":
            continue
        payload = row.get("payload") or {}
        typ = payload.get("type")
        role = payload.get("role") or typ or "?"
        if typ == "message":
            parts = []
            for item in payload.get("content") or []:
                if isinstance(item, dict):
                    parts.append(item.get("text") or "")
            out.append((role.upper(), " ".join(parts)))
        elif typ in {"function_call", "custom_tool_call"}:
            out.append(("TOOLCALL", payload.get("name") or typ))
        elif typ in {"function_call_output", "custom_tool_call_output"}:
            out.append(("TOOLRESULT", compact_text(payload.get("output"))))
        elif typ == "reasoning":
            out.append(("REASONING", compact_text(payload.get("summary") or payload.get("content"))))
    return [(role, text) for role, text in out if text.strip()], meta


def generic_text_rows(path: Path) -> list[tuple[str, str]]:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception:
        return []
    if path.suffix == ".json":
        try:
            obj = json.loads("\n".join(lines))
            return [("JSON", json.dumps(obj, ensure_ascii=False))]
        except Exception:
            pass
    return [("TEXT", line) for line in lines if line.strip()]


def file_rows(source: str, path: Path) -> tuple[list[tuple[str, str]], dict]:
    if path.suffix == ".txt" or path.suffix == ".log":
        return generic_text_rows(path), {}
    if source == "codex":
        return codex_text_rows(path)
    if source in {"claude", "hermes"} and path.suffix == ".jsonl":
        return claude_text_rows(path), {}
    return generic_text_rows(path), {}


def build_matcher(query: str | None, regex: bool, case_sensitive: bool):
    if not query:
        return None
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = query if regex else re.escape(query)
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise SystemExit(f"bad --regex pattern: {exc}") from exc


def find_matches(rows: list[tuple[str, str]], matcher, context: int) -> list[tuple[int, str]]:
    if matcher is None:
        return []
    matches = []
    for idx, (role, text) in enumerate(rows):
        if matcher.search(text):
            start = max(0, idx - context)
            end = min(len(rows), idx + context + 1)
            snippet = []
            for j in range(start, end):
                r, t = rows[j]
                prefix = ">" if j == idx else " "
                snippet.append(f"{prefix} {r}: {' '.join(t.split())[:500]}")
            matches.append((idx + 1, "\n".join(snippet)))
    return matches


def classify_claude(path: Path, rows: list[tuple[str, str]], now: float) -> tuple[str, str, str, str]:
    session_id = path.stem if path.suffix == ".jsonl" else path.parent.parent.name
    status = "TEXT/TOOL LOG"
    resume = ""
    cwd = ""
    if path.suffix != ".jsonl":
        return status, resume, cwd, session_id
    age = now - mtime(path)
    if is_live_claude_session(session_id):
        status = "LIVE (running, do not resume)"
    elif age < 60:
        status = "ACTIVE? <60s"
    elif rows:
        last_role = rows[-1][0]
        last_text = rows[-1][1]
        if last_role == "CLAUDE" and "[tool_use:" in last_text and not last_text.strip().endswith("]"):
            status = "DROPPED? (assistant/tool call at tail)"
        elif last_role == "USER" and last_text.startswith("[tool_result"):
            status = "DROPPED? (tool result at tail)"
        elif last_role == "USER":
            status = "AWAITING REPLY (user at tail)"
        else:
            status = "COMPLETED/LOGGED"
    try:
        for row in read_jsonl(path)[:40]:
            cwd = row.get("cwd") or cwd
            if cwd:
                break
    except Exception:
        pass
    if cwd and path.suffix == ".jsonl":
        resume = f'cd "{cwd}" && claude --resume {session_id} --dangerously-skip-permissions'
    elif path.suffix == ".jsonl":
        resume = f"claude --resume {session_id} --dangerously-skip-permissions"
    return status, resume, cwd, session_id


def classify_codex(path: Path, rows: list[tuple[str, str]], meta: dict, now: float, include_exec: bool) -> tuple[str, str, str, str]:
    if not meta:
        return "CODEX LOG", "", "", path.stem
    if not include_exec and meta.get("originator") == "codex_exec":
        return "SKIP_EXEC", "", "", str(meta.get("id") or path.stem)
    sid = str(meta.get("id") or path.stem)
    cwd = str(meta.get("cwd") or "")
    age = now - mtime(path)
    status = "ACTIVE? <60s" if age < 60 else "COMPLETED/LOGGED"
    if rows:
        last_role = rows[-1][0]
        if last_role in {"TOOLCALL", "TOOLRESULT", "REASONING"}:
            status = f"DROPPED? ({last_role.lower()} at tail)"
        elif last_role == "USER":
            status = "AWAITING REPLY (user at tail)"
    if meta.get("originator") == "codex_exec":
        status = f"EXEC ({status})"
    resume = f'cd "{cwd}" && codex resume {sid} --dangerously-bypass-approvals-and-sandbox' if cwd else f"codex resume {sid} --dangerously-bypass-approvals-and-sandbox"
    return status, resume, cwd, sid


def collect(args) -> list[tuple[str, Path]]:
    pairs: list[tuple[str, Path]] = []
    if args.source in {"claude", "all"}:
        pairs.extend(("claude", p) for p in iter_claude_files(args.all_projects, args.project_dir))
    if args.source in {"codex", "all"}:
        pairs.extend(("codex", p) for p in iter_codex_files(args.include_codex_exec))
    if args.source in {"hermes", "all"}:
        pairs.extend(("hermes", p) for p in iter_hermes_files())
    pairs.extend(("extra", p) for p in iter_extra_files(args.path))
    seen = set()
    unique = []
    for source, path in pairs:
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        unique.append((source, path))
    return unique


def make_record(source: str, path: Path, args, matcher, now: float) -> Record | None:
    if args.since_seconds is not None and now - mtime(path) > args.since_seconds:
        return None
    rows, meta = file_rows(source, path)
    if not rows and path.suffix not in {".txt", ".log", ".json"}:
        return None
    matches = find_matches(rows, matcher, args.context)
    if matcher is not None and not matches:
        return None
    if source == "codex":
        status, resume, cwd, sid = classify_codex(path, rows, meta, now, args.include_codex_exec)
        if status == "SKIP_EXEC":
            return None
    else:
        status, resume, cwd, sid = classify_claude(path, rows, now)
    if args.only_dropped and "DROPPED" not in status and "AWAITING" not in status:
        return None
    title = ""
    for role, text in rows[:8]:
        if role in {"SUMMARY", "USER", "CLAUDE", "ASSISTANT"} and text.strip():
            title = " ".join(text.split())[:180]
            break
    tail = rows[-args.tail :] if args.tail > 0 else []
    return Record(source, path, sid, mtime(path), cwd, title, status, resume, tail, matches)


def print_record(rec: Record, args) -> None:
    ts = datetime.fromtimestamp(rec.mtime).strftime("%Y-%m-%d %H:%M")
    print("─────────────────────────────────────────────")
    print(f"Source: {rec.source}")
    print(f"ID:     {rec.session_id}")
    print(f"Time:   {ts}")
    print(f"Path:   {rec.path}")
    if rec.cwd:
        print(f"CWD:    {rec.cwd}")
    print(f"Status: {rec.status}")
    if rec.title:
        print(f"Start:  {rec.title}")
    if rec.matches:
        print(f"Matches ({len(rec.matches)}):")
        for line_no, snippet in rec.matches[: args.max_matches]:
            print(f"  line/turn {line_no}:")
            for line in snippet.splitlines():
                print(f"    {line}")
    elif rec.tail:
        print(f"Tail (last {len(rec.tail)} msgs):")
        for role, text in rec.tail:
            print(f"  {role + ':':<10} {' '.join(text.split())[:args.tail_chars]}")
    if rec.resume:
        print(f"Resume: {rec.resume}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search/classify Claude, Codex, and Hermes agent logs")
    parser.add_argument("-q", "--query", help="keyword or regex to search for")
    parser.add_argument("--regex", action="store_true", help="treat --query as regex")
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--source", choices=["claude", "codex", "hermes", "all"], default="claude")
    parser.add_argument("--all-projects", action="store_true", help="Claude: scan every project folder")
    parser.add_argument("--project-dir", default=os.getcwd(), help="Claude project directory for slug lookup")
    parser.add_argument("--path", action="append", default=[], help="extra file or directory to search")
    parser.add_argument("--since", help="only files modified within duration, e.g. 1h, 2d")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--tail", type=int, default=4)
    parser.add_argument("--tail-chars", type=int, default=240)
    parser.add_argument("--max-matches", type=int, default=5)
    parser.add_argument("--only-dropped", action="store_true")
    parser.add_argument("--include-codex-exec", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)
    args.since_seconds = parse_since(args.since)

    now = time.time()
    matcher = build_matcher(args.query, args.regex, args.case_sensitive)
    records = []
    for source, path in collect(args):
        rec = make_record(source, path, args, matcher, now)
        if rec:
            records.append(rec)
    records.sort(key=lambda r: r.mtime, reverse=True)
    records = records[: args.limit]

    if args.json:
        print(json.dumps([{
            "source": r.source,
            "path": str(r.path),
            "session_id": r.session_id,
            "mtime": r.mtime,
            "cwd": r.cwd,
            "status": r.status,
            "title": r.title,
            "resume": r.resume,
            "matches": [{"turn": n, "snippet": s} for n, s in r.matches[: args.max_matches]],
        } for r in records], indent=2))
        return 0

    scope = args.source
    print(f"═════════════ SEARCH AGENT LOGS ({scope}) ═════════════")
    if args.query:
        print(f"query: {args.query!r}  regex={args.regex}  context={args.context}")
    if args.since:
        print(f"since: {args.since}")
    print(f"inspected matches shown: {len(records)}")
    for rec in records:
        print_record(rec, args)
    if not records:
        print("(no matching records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
