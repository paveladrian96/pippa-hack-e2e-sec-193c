"""Stops an API key, a token or a password from being committed.

NOT A BUILDER TASK, and not a file you need to change. Three things run it:

* `.githooks/pre-commit`, on the files a commit is about to contain, so a key
  is stopped before it is in the history at all;
* `scripts/check.py`, on every file git tracks here, so a clone where the
  hook was never switched on is covered too;
* you or Claude, by hand, whenever you like:

      python scripts/check_secrets.py              # every file git tracks
      python scripts/check_secrets.py --staged     # what the next commit holds
      python scripts/check_secrets.py app.py ...   # just these files

Why it matters: a key that reaches GitHub is a published key. Deleting it in
a later commit does not take it out of the history, and in a public
repository anyone can copy it from there. The only fix then is to rotate the
key with the provider. So keys never go in a file here: your app declares
them under `app_secrets:` in manifest.yaml, reads them with
`os.environ["NAME"]`, gets them on your computer from `.env` (which git never
commits) and in Pippa from Apps > Created by me > your app > Keys.
docs/API_APPS.md, "Using API keys", has the whole story.

What it looks for: keys in the formats the big providers use (AWS, GitHub,
Slack, OpenAI, Anthropic, Google, SendGrid, Hugging Face, Stripe), private
key files, `Bearer` and `Authorization` values, a long random-looking value
given to a name containing key, secret, token or password, a key in a URL
(`?api_key=...`), and files that hold keys by their nature (`.env`, `*.pem`,
`*.key`, `credentials*.json`, ...).

What it lets through: NASA's public `DEMO_KEY`, obvious placeholders
(`your-key-here`, `xxxx`, `changeme`, `<your key>`), the placeholder values
in `.env.example`, which holds names only, and, on a line ending in the
comment `# pragma: allowlist secret`, a test value that only looks like a
key. The comment never lets through a key in a provider's own format or a
private key: no test needs a real one, so one of those is always reported.

It never prints what it found, only where and what kind of thing it looks
like: its output can end up in a build log that anyone may read.

Standard library only, so it runs wherever Python 3.8 or later does, before
anything is installed.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent

#: Files larger than this are skipped, as the email scan in check.py skips them.
SCAN_LIMIT_BYTES = 1024 * 1024

#: A line containing this is not searched for values that only look like
#: keys: the way to keep a test value. Write it as a comment at the end of
#: the line. Provider formats and private keys are reported all the same.
PRAGMA = "pragma: allowlist secret"

#: The file that lists the names of the keys an app reads, with no values.
ENV_EXAMPLE = ".env.example"


@dataclass(frozen=True)
class Finding:
    """One thing that looks like a key: where it is and what kind, never the
    value itself."""

    path: str
    line: int  # 0 when it is the file itself, not a line in it
    kind: str

    def where(self) -> str:
        return f"{self.path}:{self.line}" if self.line else self.path


# ── Keys in a provider's own format ──────────────────────────────────────────
#
# These are distinctive enough to need no other evidence. They are written so
# that the same text works as a Python pattern and as a POSIX extended
# pattern for grep, because `.githooks/pre-commit` falls back to grep with
# exactly these when no Python is installed (scripts/test_check_secrets.py
# checks the hook's copy). So: no `\b`, no `\d`, no `(?:`.

PROVIDER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("an AWS access key id", r"(AKIA|ASIA)[0-9A-Z]{16}"),
    ("a GitHub token", r"gh[pousr]_[A-Za-z0-9]{36}"),
    ("a GitHub token", r"github_pat_[A-Za-z0-9_]{22,}"),
    ("a Slack token", r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    ("an Anthropic API key", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("a Google API key", r"AIza[0-9A-Za-z_-]{35}"),
    ("a SendGrid API key", r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
    ("a Hugging Face token", r"hf_[A-Za-z0-9]{30,}"),
    ("a Stripe key", r"(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"),
    ("a private key", r"-----BEGIN ([A-Z]+ )*PRIVATE KEY"),
)

#: The provider patterns as `.githooks/pre-commit` writes them: one
#: alternation, for one grep.
HOOK_PATTERN = "|".join(f"({pattern})" for _, pattern in PROVIDER_PATTERNS)

# A provider key is only one if it does not run on into more of the same
# characters: `xAKIA...` inside a longer word is not an AWS key id.
_PROVIDERS = [
    (kind, re.compile(r"(?<![A-Za-z0-9_])(" + pattern + r")(?![A-Za-z0-9])"))
    for kind, pattern in PROVIDER_PATTERNS
]

#: `sk-` followed by a long random tail: OpenAI's keys, and several others
#: copied the style. Too short a prefix to trust on its own, so the tail must
#: also look random.
_SK_KEY = re.compile(r"(?<![A-Za-z0-9_-])sk-(?!ant-)([A-Za-z0-9_-]{20,})")

# ── Keys recognised by what surrounds them ───────────────────────────────────

_BEARER = re.compile(r"(?i)(?<![A-Za-z0-9_])bearer\s+([A-Za-z0-9._~+/-]{16,}=*)")
_AUTHORIZATION = re.compile(
    r"""(?i)authorization["']?\s*[:=]\s*[rbuf]{0,2}(["'])([^"'\r\n]{16,})\1"""
)
_SCHEME = re.compile(r"(?i)^(bearer|basic|token|apikey|api-key|key)\s+")

#: Words that make a name a key's name: OPENWEATHER_API_KEY, client_secret,
#: authToken, DB_PASSWORD.
_NAME_WORDS = r"(?:key|secret|token|passwd|password|pwd|credential|appid)"
_NAME = r"[A-Za-z0-9_.-]*" + _NAME_WORDS + r"s?[A-Za-z0-9_.-]*"

#: `api_key = "..."`, `"apiKey": "..."`, `client_secret: '...'`.
_QUOTED_ASSIGNMENT = re.compile(
    r"""(?i)(?<![A-Za-z0-9_])(""" + _NAME + r""")["']?\s*(?::=|=>|=|:)\s*"""
    r"""[rbuf]{0,2}(["'])([^"'\r\n]{16,})\2"""
)
#: `API_KEY=...` in a shell script or a YAML file, with no quotes.
_BARE_ASSIGNMENT = re.compile(
    r"""(?i)^\s*(?:export\s+)?(""" + _NAME + r""")\s*[=:]\s*([^\s"'#]{16,})\s*(?:#.*)?$"""
)
#: A key written into a URL: `?api_key=...`, `&appid=...`, `?token=...`.
_URL_KEY = re.compile(
    r"(?i)[?&](api[_-]?key|apikey|key|token|access[_-]?token|auth[_-]?token|"
    r"secret|client[_-]?secret|password|appid|app[_-]?key)=([^&\s\"'#<>{}()\\]+)"
)

# ── Telling a key from a placeholder, a word or a path ───────────────────────

#: Characters a key is written with. A value with a space, a bracket or a
#: quote in it is code or prose, not a key.
_TOKEN_CHARACTERS = re.compile(r"[A-Za-z0-9+/=_.~-]+")
_HEX = re.compile(r"[0-9a-f]+|[0-9A-F]+")
_SEPARATORS = re.compile(r"[-_./]")
_PLACEHOLDER_WORDS = (
    "your", "changeme", "change_me", "change-me", "placeholder", "example",
    "dummy", "sample", "fake", "redacted", "demo_key", "notreal", "not_real",
    "not-a-real", "replace", "insert", "goes_here", "goes-here", "here",
    "todo", "xxx",
)


def is_placeholder(value: str) -> bool:
    """Whether a value is obviously not a real key: `your-key-here`, `xxxx`,
    `<api key>`, `changeme`, `${API_KEY}`, NASA's public `DEMO_KEY`, or one
    character over and over."""
    lowered = value.lower()
    if "<" in value and ">" in value:
        return True
    if "${" in value or "{{" in value or "%(" in value:
        return True
    if any(word in lowered for word in _PLACEHOLDER_WORDS):
        return True
    if "..." in value or "***" in value:
        return True
    return len(set(lowered)) <= 2


def entropy(value: str) -> float:
    """Shannon entropy in bits per character: about 4 to 6 for a random key,
    lower for words and repeated characters."""
    if not value:
        return 0.0
    counts = {}
    for character in value:
        counts[character] = counts.get(character, 0) + 1
    total = len(value)
    return -sum(n / total * math.log2(n / total) for n in counts.values())


def looks_random(value: str, min_length: int = 16) -> bool:
    """Whether a value looks like a generated key rather than a word, a name,
    a path or a placeholder.

    A key is long, uses only the characters keys use, mixes in digits (or,
    with none, both cases at length), and is not made of ordinary words
    joined by `-`, `_`, `.` or `/` (`value-of-some-thing-v2`, `src/app.py`).
    """
    if len(value) < min_length or not _TOKEN_CHARACTERS.fullmatch(value):
        return False
    if is_placeholder(value) or "://" in value:
        return False
    parts = [part for part in _SEPARATORS.split(value) if part]
    # One long random part is enough (`proj-<48 random characters>`); without
    # one, mostly words is a name.
    long_random = any(
        len(part) >= 16 and not part.isalpha() and not part.isdigit() for part in parts
    )
    if len(parts) >= 2 and not long_random:
        words = sum(1 for part in parts if part.isalpha())
        if words * 2 >= len(parts):
            return False
    has_digit = any(c.isdigit() for c in value)
    has_lower = any(c.islower() for c in value)
    has_upper = any(c.isupper() for c in value)
    if has_digit and (has_lower or has_upper):
        # Hex is only 16 symbols, so it scores lower for the same randomness;
        # a short one is more often a colour or a hash prefix than a key.
        if _HEX.fullmatch(value):
            return len(value) >= 20 and entropy(value) >= 3.0
        return entropy(value) >= 3.0
    if not has_digit and has_lower and has_upper:
        return len(value) >= 24 and entropy(value) >= 4.0
    return False


# ── Files that hold keys by their nature ─────────────────────────────────────

_KEY_FILE_PATTERNS = (
    (re.compile(r"\.env(\..+)?"), "an environment file (.env) holds keys: it stays on your computer"),
    (re.compile(r".+\.env"), "an environment file holds keys: it stays on your computer"),
    (re.compile(r".+\.(pem|key|p12|pfx|jks|keystore)", re.IGNORECASE), "a private key or certificate file"),
    (re.compile(r"id_(rsa|dsa|ecdsa|ed25519)"), "an SSH private key"),
    (re.compile(r"credentials.*\.json", re.IGNORECASE), "a credentials file"),
    (re.compile(r"(client_)?secrets?\.json", re.IGNORECASE), "a secrets file"),
    (re.compile(r"\.(netrc|pypirc|npmrc)"), "a file that holds a login or a token"),
)


def key_file_kind(path: str) -> Optional[str]:
    """What kind of key file `path` is by its name, or None.

    `.env.example` is fine, and is what the template ships: it lists names,
    never values. So is a public SSH key, `id_rsa.pub`.
    """
    name = PurePosixPath(path.replace("\\", "/")).name
    if name == ENV_EXAMPLE or name.endswith(".pub"):
        return None
    for pattern, kind in _KEY_FILE_PATTERNS:
        if pattern.fullmatch(name):
            return kind
    return None


# ── .env.example ─────────────────────────────────────────────────────────────

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def _env_value(raw: str) -> str:
    """A value from a `NAME=value` line: quotes taken off, or a trailing
    ` # comment` when it has none."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    return re.sub(r"\s+#.*$", "", raw)


def env_example(text: str, path: str = ENV_EXAMPLE) -> tuple[frozenset[str], list[Finding]]:
    """The values in `.env.example` that every other file may contain, and
    the lines of it that hold what looks like a real key.

    It should hold names only (`OPENWEATHER_API_KEY=`), so a value in it is a
    placeholder at most. A value that looks like a real key is reported, not
    allowed: `.env.example` is committed.

    Every line is searched, comments included: the template ships commented
    lines such as `# OPENWEATHER_API_KEY=`, and filling one in without taking
    the `#` off still commits the key. A commented `# NAME=value` is judged
    like an uncommented one, and any line is searched as every other file's
    lines are (a provider's key format, a key in a URL, ...). Only an
    uncommented placeholder value is allowed elsewhere.
    """
    allowed, findings = set(), []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        commented = stripped.startswith("#")
        kinds: list[str] = []
        match = _ENV_LINE.match(stripped.lstrip("#") if commented else line)
        if match:
            value = _env_value(match.group(2))
            if value and (_provider_kind(value) or (PRAGMA not in line and looks_random(value))):
                kinds.append(f"a value for {match.group(1)} that looks like a real key "
                             f"({ENV_EXAMPLE} holds names only)")
            elif value and not commented:
                allowed.add(value)
        if not kinds:
            kinds = scan_line(line)
        findings.extend(Finding(path, number, kind) for kind in kinds)
    return frozenset(allowed), findings


# ── Scanning ─────────────────────────────────────────────────────────────────

def _provider_kind(text: str) -> Optional[str]:
    for kind, pattern in _PROVIDERS:
        for match in pattern.finditer(text):
            if not is_placeholder(match.group(1)):
                return kind
    return None


_NAME_WORD = re.compile(_NAME_WORDS, re.IGNORECASE)
_NAME_PARTS = re.compile(r"[-_.]|(?<=[a-z0-9])(?=[A-Z])")

#: The longest name a finding repeats. Past this it says only the word.
SHOWN_NAME_MAX = 40


def shown_name(name: str) -> str:
    """The part of a name that a finding may print.

    The name pattern is greedy, so in `cfg.token_3f9a... = "3f9a..."` the
    "name" runs on into characters that may be the key itself. So the name
    is cut after its last key word (`OPENWEATHER_API_KEY`, `cfg.token`), and
    when what is left is long or has a random-looking part in it, only the
    word itself is printed (`token`).
    """
    words = list(_NAME_WORD.finditer(name))
    if not words:
        return "a name"
    last = words[-1]
    cut = name[:last.end()]
    parts = [part for part in _NAME_PARTS.split(cut) if part]
    if len(cut) > SHOWN_NAME_MAX or any(looks_random(part, 8) for part in parts):
        return last.group(0)
    return cut


def scan_line(line: str, allowed: frozenset[str] = frozenset()) -> list[str]:
    """The kinds of key in one line, without saying what they are.

    A line with `# pragma: allowlist secret` on it is not searched for keys
    recognised by their surroundings (a long random value given to a key's
    name, a Bearer value, a key in a URL): a test can need a value like that.
    It is still searched for keys in a provider's own format and for private
    keys, because no test needs a real one of those, and a comment must not
    be enough to let a real one through.
    """
    kinds: list[str] = []

    def found(kind: str, value: str, min_length: int = 16, random_check: bool = True) -> None:
        value = value.strip()
        if value in allowed or is_placeholder(value):
            return
        if random_check and not looks_random(value, min_length):
            return
        if kind not in kinds:
            kinds.append(kind)

    for kind, pattern in _PROVIDERS:
        for match in pattern.finditer(line):
            found(kind, match.group(1), random_check=False)
    for match in _SK_KEY.finditer(line):
        found("a secret key (sk-...)", match.group(1), min_length=20)
    if PRAGMA in line:
        return kinds
    for match in _BEARER.finditer(line):
        found("a Bearer token", match.group(1))
    for match in _AUTHORIZATION.finditer(line):
        found("an Authorization header value", _SCHEME.sub("", match.group(2).strip()))
    for match in _QUOTED_ASSIGNMENT.finditer(line):
        found(f"a key-like value given to {shown_name(match.group(1))}", match.group(3))
    match = _BARE_ASSIGNMENT.match(line)
    if match:
        found(f"a key-like value given to {shown_name(match.group(1))}", match.group(2))
    for match in _URL_KEY.finditer(line):
        found(f"a key in a URL ({match.group(1)}=)", match.group(2), min_length=12)
    return kinds


def scan_text(path: str, text: str, allowed: frozenset[str] = frozenset()) -> list[Finding]:
    """Every line of `text` that looks as if it holds a key."""
    if PurePosixPath(path.replace("\\", "/")).name == ENV_EXAMPLE:
        return env_example(text, path)[1]
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind in scan_line(line, allowed):
            findings.append(Finding(path, number, kind))
    return findings


def _decode(data: bytes) -> Optional[str]:
    """The text of a file, or None for a binary or an oversized one."""
    if len(data) > SCAN_LIMIT_BYTES or b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def scan_blobs(blobs: Iterable[tuple[str, Optional[bytes]]],
               allowed: frozenset[str] = frozenset()) -> list[Finding]:
    """Findings for (path, contents) pairs. A file that holds keys by its
    name is reported whatever is in it; contents of None mean "name only"."""
    findings = []
    for path, data in blobs:
        kind = key_file_kind(path)
        if kind:
            findings.append(Finding(path, 0, kind))
            continue
        text = _decode(data) if data is not None else None
        if text is not None:
            findings.extend(scan_text(path, text, allowed))
    return findings


def _git(root: Path, *args: str) -> Optional[bytes]:
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=30)
    except Exception:
        return None
    return done.stdout if done.returncode == 0 else None


def _names(output: Optional[bytes]) -> list[str]:
    if output is None:
        return []
    return [name for name in output.decode("utf-8", errors="replace").split("\0") if name]


def _allowed_from(text: Optional[str]) -> frozenset[str]:
    return env_example(text)[0] if text else frozenset()


def scan_tree(root: Path = ROOT) -> Optional[list[Finding]]:
    """Every file git tracks under `root`, as it is on disk. None when this
    is not a git repository, so nothing can be committed from it anyway.

    Only tracked files: a `.env` that git ignores is where keys belong.
    """
    listing = _git(root, "ls-files", "-z")
    if listing is None:
        return None
    names = _names(listing)
    example = root / ENV_EXAMPLE
    allowed = _allowed_from(example.read_text(encoding="utf-8", errors="replace")
                            if example.is_file() else None)

    def blobs():
        for name in names:
            path = root / name
            try:
                if not path.is_file() or path.stat().st_size > SCAN_LIMIT_BYTES:
                    yield name, None  # its name is still checked
                    continue
                yield name, path.read_bytes()
            except OSError:
                yield name, None

    return scan_blobs(blobs(), allowed)


def scan_staged(root: Path = ROOT) -> Optional[list[Finding]]:
    """The files the next commit adds or changes, as they are staged: what
    the commit will contain, not what is on disk."""
    listing = _git(root, "-c", "core.quotepath=off", "diff", "--cached", "--name-only",
                   "-z", "--diff-filter=ACMR")
    if listing is None:
        return None
    names = _names(listing)
    staged_example = _git(root, "show", f":{ENV_EXAMPLE}")
    allowed = _allowed_from(staged_example.decode("utf-8", errors="replace")
                            if staged_example is not None else None)

    def blobs():
        for name in names:
            yield name, _git(root, "show", f":{name}")

    return scan_blobs(blobs(), allowed)


def scan_paths(paths: Iterable[str], root: Path = ROOT) -> list[Finding]:
    """These files, as they are on disk."""
    example = root / ENV_EXAMPLE
    allowed = _allowed_from(example.read_text(encoding="utf-8", errors="replace")
                            if example.is_file() else None)

    def blobs():
        for name in paths:
            path = Path(name)
            try:
                yield name, path.read_bytes() if path.is_file() else None
            except OSError:
                yield name, None

    return scan_blobs(blobs(), allowed)


ADVICE = """\
Keys never go in a file in this repository: anything committed can be read by
everyone who can see it, and stays in the history after it is deleted.

  * Declare the key in manifest.yaml under app_secrets, and read it in your
    code with os.environ["NAME"].
  * On your computer, put the value in .env (git never commits it).
  * For the published app, set it in Pippa: Apps > Created by me > your app >
    Keys. Changing it there needs no push.

If a real key was ever pushed, rotate it with the provider FIRST (make a new
one, delete the old one): deleting it from the code does not make it safe.

If a line in a test only looks like a key (a made-up value, not one from a
provider), it may end with the comment `# pragma: allowlist secret`. Never
add that comment to make a real key pass: a key in a provider's format (AWS,
GitHub, OpenAI, ...) is reported with it or without it. docs/API_APPS.md,
"Using API keys", has more."""


def report(findings: list[Finding]) -> str:
    lines = [f"  {finding.where()}: {finding.kind}" for finding in findings]
    return "\n".join(lines)


def repository_root() -> Path:
    """The top of the git repository the command is run in: the one a commit
    is being made in, when the hook runs this. This file's own repository
    when the command is not run inside one."""
    top = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    if top:
        return Path(top.decode("utf-8", errors="replace").strip())
    return ROOT


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = repository_root()
    if args == ["--staged"]:
        findings = scan_staged(root)
        what = "the staged files"
    elif args:
        if any(arg.startswith("-") for arg in args):
            print(f"Unknown option. Usage: python {Path(__file__).name} [--staged | FILE ...]")
            return 2
        findings = scan_paths(args, root)
        what = "those files"
    else:
        findings = scan_tree(root)
        what = "the files git tracks"
    if findings is None:
        print("Not a git repository, so there is nothing to check.")
        return 2
    if not findings:
        print(f"No keys found in {what}.")
        return 0
    print("This looks like a key, a token or a password:")
    print(report(findings))
    print()
    print(ADVICE)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
