"""Reads `.env` into the environment, for running the app on your computer.

NOT A BUILDER TASK, and not a file you need to change. `conftest.py` (so
every `pytest` run) and `scripts/check.py` call `load()` before the app runs.

In Pippa, your app's keys come from Apps > Created by me > your app > Keys,
and arrive in `os.environ` for each call. On your computer they come from a
file called `.env` at the top of the repository, one per line:

    OPENWEATHER_API_KEY=the-value-from-the-provider

`.gitignore` keeps `.env` out of every commit, and `.env.example` lists the
same names with no values, so a fresh copy knows what to fill in.

Rules, the usual ones for a `.env` file:

* `NAME=value`, optionally after `export `; blank lines and lines starting
  with `#` are skipped.
* A value may be in single or double quotes, which are taken off. Without
  quotes, a ` # comment` after it is taken off.
* A name that is already set in the environment is left alone, so a value
  you set in the terminal wins over the file.

It never prints a value. Standard library only.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import MutableMapping, Optional

ROOT = Path(__file__).resolve().parent.parent

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse(text: str) -> dict[str, str]:
    """The `NAME=value` pairs in the text of a `.env` file, in order."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE.match(line)
        if not match:
            continue
        name, raw = match.group(1), match.group(2)
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
            value = raw[1:-1]
        else:
            value = re.sub(r"\s+#.*$", "", raw)
        values[name] = value
    return values


def load(path: Optional[Path] = None,
         environ: Optional[MutableMapping[str, str]] = None) -> list[str]:
    """Put the values from `.env` into the environment, leaving every name
    that is already set alone. Returns the names it set (never the values).

    No `.env`, or one that cannot be read, is not an error: most runs,
    including every build, have none.
    """
    path = ROOT / ".env" if path is None else path
    environ = os.environ if environ is None else environ
    try:
        # utf-8-sig: Notepad on Windows starts a file with a byte-order mark,
        # which would otherwise become part of the first name.
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    loaded = []
    for name, value in parse(text).items():
        if name not in environ:
            environ[name] = value
            loaded.append(name)
    return loaded
