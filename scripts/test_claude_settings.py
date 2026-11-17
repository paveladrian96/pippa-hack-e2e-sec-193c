"""Tests for `.claude/settings.json`, which keeps Claude Code out of `.env`.

NOT a test of your app. If one of these fails, `.claude/settings.json` (or
`.gitignore`) was changed or deleted: put back the rules the failure names.
They stop Claude Code opening, writing or creating `.env` (where your keys
live on this computer) and its copies under other names, so a key never ends
up in a conversation with Claude. They also close
`.claude/settings.local.json`, Claude Code's settings for this computer only,
which can hold a key Claude Code itself uses. `.env.example`, which holds
names and no values, stays open: Claude keeps it up to date.

The rules use only `*` and `?`, never `[...]`, so every way of matching a path
(gitignore's, a shell's) reads them the same way, and these tests can check
them with `fnmatch`. Deny rules always win over allow rules in Claude Code, so
"deny `.env.*`, allow `.env.example`" would block `.env.example` too: hence
the longer list. For the same reason a name of exactly seven letters after
`.env.` (`.env.develop`) is closed only when it is listed by name: a pattern
for every such name would also match `.env.example`.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"
GITIGNORE = ROOT / ".gitignore"

#: Claude Code's tools for reading files (Read; Grep and Glob follow its rules)
#: and for changing them (Edit; Write follows its rules).
TOOLS = ("Read", "Edit")

#: Files that hold, or could hold, real values. Every one must be closed to
#: both tools.
SECRET_FILES = (
    ".env",
    ".env.local", ".env.dev", ".env.prod", ".env.test", ".env.old", ".env.bak",
    ".env.save", ".env.backup", ".env.staging", ".env.testing", ".env.default",
    ".env.preview", ".env.secrets", ".env.private", ".env.release",
    ".env.development", ".env.production", ".env.examples",
    ".env.production.local", ".env.example.local", ".env.example.bak",
    "local.env", "prod.env",
    # Copies under other names: an editor's backup, what Windows Explorer
    # names a copy, a dash or an underscore instead of the dot, direnv's file.
    ".env~", ".env - Copy", ".env - Copy (2)", ".env-prod", ".env-local",
    ".env_local", ".env_prod", ".envrc",
)

#: Claude Code's settings for this computer only (git ignores it). It can
#: hold a key Claude Code itself uses, in its `env`. Closed to both tools.
LOCAL_SETTINGS = ".claude/settings.local.json"

#: Names only, no values: committed, and kept up to date by Claude.
OPEN_FILES = (".env.example",)

#: A rule for one tool: `Read(<pattern>)`, or `Read` alone (every file).
RULE = re.compile(r"^(?P<tool>[A-Za-z]+)(?:\((?P<pattern>[^()]*)\))?$")

#: Ways a pattern can start that still mean "this repository's top level".
ANCHORS = ("./", "**/", "/")

#: What a pattern may contain: literal file-name characters (a space and `~`
#: included), `*` and `?`.
PLAIN_PATTERN = re.compile(r"^[A-Za-z0-9._~ *?-]+$")

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def _settings() -> dict:
    assert SETTINGS.is_file(), (
        ".claude/settings.json is missing. It keeps Claude Code from opening "
        ".env, where your keys are: restore it from the template."
    )
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f".claude/settings.json is not valid JSON ({exc.msg}, line {exc.lineno}), "
            "so Claude Code ignores it and can open .env. Fix the JSON."
        ) from None
    assert isinstance(data, dict), ".claude/settings.json must be one JSON object."
    return data


def _list(data: dict, kind: str) -> list:
    permissions = data.get("permissions", {})
    assert isinstance(permissions, dict), '"permissions" in .claude/settings.json must be an object.'
    rules = permissions.get(kind, [])
    assert isinstance(rules, list) and all(isinstance(r, str) for r in rules), (
        f'"permissions.{kind}" in .claude/settings.json must be a list of strings.'
    )
    return rules


def _patterns(rules, tool: str) -> list[str]:
    """The file patterns `tool`'s rules name, as top-level file names."""
    out = []
    for rule in rules:
        match = RULE.match(rule.strip())
        if not match or match["tool"] != tool:
            continue
        pattern = (match["pattern"] or "*").strip() or "*"
        stripped = True
        while stripped:
            stripped = False
            for anchor in ANCHORS:
                if pattern.startswith(anchor):
                    pattern, stripped = pattern[len(anchor):], True
        out.append(pattern)
    return out


def _closed_by(patterns, name: str) -> list[str]:
    return [p for p in patterns if fnmatch.fnmatchcase(name, p)]


def test_the_settings_are_valid_json_with_a_deny_list():
    data = _settings()
    deny = _list(data, "deny")
    assert deny, '.claude/settings.json has no "permissions": {"deny": [...]} rules.'
    assert len(deny) == len(set(deny)), "a rule is listed twice in permissions.deny"


def test_dot_env_is_closed_to_reading_and_writing():
    deny = _list(_settings(), "deny")
    for tool in TOOLS:
        assert f"{tool}(./.env)" in deny, (
            f'.claude/settings.json must deny "{tool}(./.env)": it keeps Claude '
            "Code out of the file that holds your keys. Put the rule back."
        )
        patterns = _patterns(deny, tool)
        still_open = [name for name in SECRET_FILES if not _closed_by(patterns, name)]
        assert not still_open, (
            f"Claude Code's {tool} tool can still open {', '.join(still_open)}: "
            ".claude/settings.json must deny every .env file but .env.example. "
            "Put back the template's rules."
        )


def test_claude_code_s_local_settings_are_closed_to_reading_and_writing():
    deny = _list(_settings(), "deny")
    for tool in TOOLS:
        assert _closed_by(_patterns(deny, tool), LOCAL_SETTINGS), (
            f'.claude/settings.json must deny "{tool}(./{LOCAL_SETTINGS})": that '
            "file can hold a key Claude Code itself uses. Put the rule back."
        )


def test_dot_env_example_stays_open():
    data = _settings()
    for kind in ("deny", "ask"):
        rules = _list(data, kind)
        for tool in TOOLS:
            for name in OPEN_FILES:
                closing = _closed_by(_patterns(rules, tool), name)
                assert not closing, (
                    f"{tool}({', '.join(closing)}) in permissions.{kind} also blocks "
                    f"{name}, which holds only names and which Claude keeps up to "
                    "date. A deny always wins over an allow, so narrow the rule instead."
                )


def test_the_env_patterns_mean_the_same_to_every_matcher():
    deny = _list(_settings(), "deny")
    for rule in deny:
        match = RULE.match(rule.strip())
        inner = (match["pattern"] or "") if match else ""
        assert rule == rule.strip() and inner == inner.strip(), (
            f"{rule!r}: a rule may not have a space at either end, or just inside "
            "its brackets. gitignore drops a space at the end of a pattern, so "
            "matchers would no longer agree on the files it closes."
        )
    for tool in TOOLS:
        for pattern in _patterns(deny, tool):
            if not any(_closed_by([pattern], name) for name in SECRET_FILES):
                continue  # not a rule about .env files
            assert PLAIN_PATTERN.match(pattern), (
                f"{tool}(./{pattern}): use only letters, digits, '.', '-', '_', "
                "'~', a space, '*' and '?' in a .env rule. Brackets and '!' mean "
                "different things to different matchers."
            )


def _git_ignored(tmp_path: Path, names) -> set[str]:
    """Which of `names` this repository's `.gitignore` alone makes git ignore:
    checked in an empty repository, so no other ignore file has a say."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    (repo / ".gitignore").write_bytes(GITIGNORE.read_bytes())
    no_global = tmp_path / "no-global-ignore"
    no_global.write_text("", encoding="utf-8")
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", f"core.excludesFile={no_global.as_posix()}",
         "check-ignore", "--no-index", *names],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode in (0, 1), result.stderr
    return {line for line in result.stdout.splitlines() if line}


@needs_git
def test_git_ignores_every_env_file_but_the_example(tmp_path):
    assert GITIGNORE.is_file(), ".gitignore is missing: restore it from the template."
    ignored = _git_ignored(tmp_path, SECRET_FILES + OPEN_FILES + (LOCAL_SETTINGS,))
    committable = [name for name in SECRET_FILES + (LOCAL_SETTINGS,) if name not in ignored]
    assert not committable, (
        f"git would commit {', '.join(committable)}: .gitignore must keep every "
        ".env file but .env.example out of the repository. Put back the "
        "template's lines."
    )
    hidden = [name for name in OPEN_FILES if name in ignored]
    assert not hidden, (
        f".gitignore also ignores {', '.join(hidden)}, which holds only names and "
        "is committed. Narrow the line that matches it."
    )
