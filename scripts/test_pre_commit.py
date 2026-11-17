"""Tests for .githooks/pre-commit, the hook that stops a commit carrying an
email address, or a name that is not the public pseudonym.

NOT a test of your app, and not a file you need to touch. Each test makes a
throwaway repository in a temporary folder, switches the hook on there, and
makes real commits through git, so what is tested is what git runs. They need
git, and nothing else: git runs the hook with its own sh, Git for Windows
included.

The hook is in sh and cannot import anything, so it keeps its own copy of the
four patterns scripts/check.py uses. The first test is the one that notices
when the copies drift apart, and the line-by-line test below runs the same
lines through both.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".githooks"
HOOK = HOOKS / "pre-commit"

# Written out, an address that is nobody's but outside the allowed domains
# would be exactly what the build refuses, so it is put together here instead.
# `.local` is a machine's name on its own network: what git puts on a commit
# when nobody has set an address.
AT = "@"
PERSONAL = f"pat{AT}laptop.local"
NOREPLY = "12345+tidewatcher@users.noreply.github.com"

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def test_the_hook_finds_addresses_exactly_as_check_py_does():
    text = HOOK.read_text(encoding="utf-8")
    email = re.search(r"^email_re='([^']*)'$", text, re.MULTILINE)
    allowed = re.search(r"^allowed_re='([^']*)'$", text, re.MULTILINE)
    file_suffix = re.search(r"^file_suffix_re='([^']*)'$", text, re.MULTILINE)
    noreply = re.search(r"^noreply_re='([^']*)'$", text, re.MULTILINE)
    assert email and email.group(1) == check.EMAIL_PATTERN
    assert allowed and allowed.group(1) == check.ALLOWED_PATTERN
    assert file_suffix and file_suffix.group(1) == check.FILE_SUFFIX_PATTERN
    assert noreply and noreply.group(1) == check.NOREPLY_PATTERN


def test_the_hook_keeps_unix_line_endings():
    """A carriage return turns every line of a shell script into a command
    that does not exist. `.gitattributes` keeps it out of every checkout."""
    assert b"\r" not in HOOK.read_bytes()
    assert ".githooks/* text eol=lf" in (ROOT / ".gitattributes").read_text(encoding="utf-8")


class Repo:
    """A throwaway repository with the hook switched on, as Claude does it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        # Nothing from this machine's own git settings: no signing, no global
        # hooks, no line-ending conversion.
        self.env = {
            **os.environ,
            "HOME": str(path.parent),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(path.parent / "empty.gitconfig"),
            "LC_ALL": "C",
            # The key check runs with the Python running these tests, whatever
            # is on PATH. The fallback tests below set "none".
            "PIPPA_HOOK_PYTHON": Path(sys.executable).as_posix(),
        }
        for name in [n for n in self.env if n.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_"))]:
            del self.env[name]
        (path.parent / "empty.gitconfig").write_text("", encoding="utf-8")
        path.mkdir()
        self.git("init", "-q")
        self.git("config", "core.hooksPath", HOOKS.as_posix())
        self.git("config", "user.name", "Tidewatcher")
        self.git("config", "user.email", NOREPLY)

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=self.path, env=self.env,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )

    def commit(self, files: dict[str, str | bytes]) -> subprocess.CompletedProcess:
        for name, content in files.items():
            self.write(name, content)
            self.git("add", name)
        return self.git("commit", "-q", "-m", "test")

    def write(self, name: str, content: str | bytes) -> None:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path / "repo")


@needs_git
def test_a_clean_commit_goes_through(repo):
    done = repo.commit({"app.py": "print('hello')\n", "README.md": "See you@example.com\n"})
    assert done.returncode == 0, done.stderr


@needs_git
def test_a_commit_with_a_personal_address_on_it_is_stopped(repo):
    repo.git("config", "user.email", PERSONAL)
    done = repo.commit({"app.py": "print('hello')\n"})
    assert done.returncode != 0
    assert "author: p***@laptop.local" in done.stderr
    assert "users.noreply.github.com" in done.stderr
    assert PERSONAL not in done.stderr
    assert repo.git("rev-parse", "--verify", "-q", "HEAD").returncode != 0


@needs_git
def test_an_address_in_a_staged_file_is_stopped_and_named_by_line(repo):
    done = repo.commit({"docs/notes.md": f"one\ntwo\nwrite to {PERSONAL}\n"})
    assert done.returncode != 0
    assert "docs/notes.md:3: p***@laptop.local" in done.stderr
    assert PERSONAL not in done.stderr


@needs_git
def test_the_staged_copy_is_what_counts(repo):
    """Fixing the file on disk without staging it again fixes nothing: the
    commit would still contain the address."""
    (repo.path / "notes.md").write_text(f"{PERSONAL}\n", encoding="utf-8")
    repo.git("add", "notes.md")
    (repo.path / "notes.md").write_text("fixed\n", encoding="utf-8")
    assert repo.git("commit", "-q", "-m", "test").returncode != 0
    repo.git("add", "notes.md")
    assert repo.git("commit", "-q", "-m", "test").returncode == 0


@needs_git
def test_binary_files_are_not_read(repo):
    done = repo.commit({"logo.png": b"\x89PNG\0\0" + PERSONAL.encode()})
    assert done.returncode == 0, done.stderr


@needs_git
def test_the_templates_own_files_go_through(repo):
    """Lines from this template that look a little like addresses."""
    page = (
        '<script type="module">import m from '
        '"https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";</script>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600">\n'
    )
    code = '@pytest.mark.network\nexample = f"@{manifest.name} {first}"\n'
    done = repo.commit({"builder-guide.html": page, "test_x.py": code})
    assert done.returncode == 0, done.stderr


@needs_git
def test_a_file_name_that_looks_like_an_address_goes_through(repo):
    """The build lets these through, so the hook must too: refused here, they
    could only be committed with `--no-verify`, which CLAUDE.md forbids."""
    page = (
        '<img src="img/logo@2x.png" srcset="img/logo@3X.WEBP 3x">\n'
        '<script src="vendor/lib@1.2.3.min.js"></script>\n'
    )
    done = repo.commit({"index.html": page})
    assert done.returncode == 0, done.stderr


@needs_git
def test_an_address_next_to_a_file_name_is_still_stopped(repo):
    done = repo.commit({"index.html": f'<img src="logo@2x.png"> mail {PERSONAL}\n'})
    assert done.returncode != 0
    assert "index.html:1: p***@laptop.local" in done.stderr
    assert "2x.png" not in done.stderr


@needs_git
def test_the_hook_and_check_py_find_the_same_addresses_line_by_line(repo):
    """The same lines through both, so that the hook never stops a commit over
    a line check.py would pass, nor the other way round."""
    lines = [
        f"write to {PERSONAL} today",
        '<img src="logo@2x.png" alt="">',
        "background: url(arrow@3x.webp);",
        f"jo{AT}uni.ac.uk and you@example.com",
        "ICON@2X.PNG",
        f"pat{AT}laptop.apng",
        "import m from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'",
        NOREPLY,
    ]
    done = repo.commit({"notes.md": "\n".join(lines) + "\n"})
    reported = re.findall(r"^  notes\.md:(\d+): (\S+)$", done.stderr, re.MULTILINE)
    expected = [
        (str(number), check.mask(address))
        for number, address in check.addresses_in("\n".join(lines))
    ]
    assert expected == [("1", "p***@laptop.local"), ("4", "j***@uni.ac.uk"),
                        ("6", "p***@laptop.apng")]
    assert reported == expected, done.stderr


@needs_git
def test_githubs_own_address_on_the_commit_goes_through(repo):
    """What GitHub puts on an edit made on its website, and the build
    accepts. Put together here: written out, the build would refuse this file."""
    repo.env["GIT_COMMITTER_EMAIL"] = f"noreply{AT}github.com"
    done = repo.commit({"app.py": "print('hello')\n"})
    assert done.returncode == 0, done.stderr


# ── The name on the commit ───────────────────────────────────────────────────

def manifest(author_line: str) -> str:
    """A manifest.yaml with only the line the hook reads, and a neighbour."""
    return f"manifest_version: 1\n{author_line}\napp:\n  id: hack.tide_times\n"


@needs_git
def test_the_pseudonym_on_the_commit_goes_through(repo):
    done = repo.commit({"manifest.yaml": manifest('app_author_name: "Tidewatcher"')})
    assert done.returncode == 0, done.stderr


@needs_git
def test_a_name_that_is_not_the_pseudonym_is_stopped(repo):
    """What a fresh clone on another computer does: git takes the name from
    that computer's settings, usually the person's real one."""
    repo.git("config", "user.name", "Somebody Else")
    done = repo.commit({"manifest.yaml": manifest('app_author_name: "Tidewatcher"')})
    assert done.returncode != 0
    assert "The name on the commit (author, committer) is not your public author name" in done.stderr
    assert 'git config user.name "Tidewatcher"' in done.stderr
    assert "Somebody Else" not in done.stderr
    assert repo.git("rev-parse", "--verify", "-q", "HEAD").returncode != 0


@needs_git
def test_the_committer_name_counts_too(repo):
    repo.env["GIT_COMMITTER_NAME"] = "Somebody Else"
    done = repo.commit({"manifest.yaml": manifest('app_author_name: "Tidewatcher"')})
    assert done.returncode != 0
    assert "The name on the commit (committer)" in done.stderr


@needs_git
def test_the_pseudonym_is_read_however_yaml_lets_it_be_written(repo):
    repo.git("config", "user.name", "Tide watcher")
    for line in (
        'app_author_name: "Tide watcher"',
        "app_author_name: 'Tide watcher'",
        "app_author_name: Tide watcher   # shown as by Tide watcher",
        'app_author_name:   "  Tide   watcher "',
        "app_author_name:\t'Tide\twatcher'",
    ):
        done = repo.commit({"manifest.yaml": manifest(line), "n.txt": line})
        assert done.returncode == 0, (line, done.stderr)


@needs_git
def test_a_manifest_with_windows_line_endings_is_read(repo):
    """Unquoted, so that a carriage return left on the end would be part of
    the name and match nothing."""
    text = manifest("app_author_name: Tidewatcher").replace("\n", "\r\n")
    repo.git("config", "core.autocrlf", "false")
    assert repo.commit({"manifest.yaml": text.encode()}).returncode == 0
    repo.git("config", "user.name", "Somebody Else")
    assert repo.commit({"manifest.yaml": (text + "#\r\n").encode()}).returncode != 0


@needs_git
def test_the_staged_manifest_is_what_counts(repo):
    """The commit carries the staged manifest, so its name is the one that
    has to match, not an edit that has not been staged yet."""
    repo.commit({"manifest.yaml": manifest('app_author_name: "Tidewatcher"')})
    repo.write("manifest.yaml", manifest('app_author_name: "Night Owl"'))
    assert repo.commit({"app.py": "print('hello')\n"}).returncode == 0
    repo.git("config", "user.name", "Night Owl")
    done = repo.commit({"app.py": "print('hello again')\n"})
    assert done.returncode != 0
    assert "stage manifest.yaml too" in done.stderr
    repo.git("add", "manifest.yaml")
    assert repo.git("commit", "-q", "-m", "test").returncode == 0


@needs_git
def test_while_the_pseudonym_is_empty_a_name_must_be_set_for_this_repository(repo):
    """The template ships `app_author_name: ""`. Nothing to compare with yet,
    so at least not the name from this computer's own git settings."""
    (repo.path.parent / "empty.gitconfig").write_text(
        "[user]\n\tname = Computer Owner\n", encoding="utf-8",
    )
    repo.git("config", "--unset", "user.name")
    done = repo.commit({"manifest.yaml": manifest('app_author_name: ""')})
    assert done.returncode != 0
    assert "No name is set for this repository." in done.stderr
    assert "Computer Owner" not in done.stderr
    repo.git("config", "user.name", "Tidewatcher")
    assert repo.git("commit", "-q", "-m", "test").returncode == 0


@needs_git
def test_without_a_manifest_a_name_must_be_set_for_this_repository(repo):
    """Repo sets user.name for the repository, as Claude does in step 1, and
    that is enough; the name from this computer's own settings is not."""
    assert repo.commit({"app.py": "print('hello')\n"}).returncode == 0
    repo.git("config", "--unset", "user.name")
    (repo.path.parent / "empty.gitconfig").write_text(
        "[user]\n\tname = Computer Owner\n", encoding="utf-8",
    )
    assert repo.commit({"app.py": "print('hello again')\n"}).returncode != 0


@needs_git
def test_a_name_ending_in_a_dot_matches(repo):
    """Some versions of git leave dots off the end of the name on a commit."""
    repo.git("config", "user.name", "Night Owl")
    assert repo.commit({"manifest.yaml": manifest('app_author_name: "Night Owl."')}).returncode == 0


# ── Keys ─────────────────────────────────────────────────────────────────────
#
# No key is written out here: each is put together while the test runs, so
# this file never looks like a leak itself.

AWS_LIKE = "AKIA" + "J7Q2" + "M4XZ" + "8B3K" + "P6TW"
HEX_KEY = "".join("0a1b2c3d4e5f6a7b8c9d"[i % 20] for i in range(7, 39))


@needs_git
def test_a_key_in_a_staged_file_is_stopped_and_never_shown(repo):
    done = repo.commit({"app.py": f'import os\nWEATHER_API_KEY = "{HEX_KEY}"\n'})
    assert done.returncode != 0
    assert "looks as if it holds a key" in done.stderr
    assert "app.py:2: a key-like value given to WEATHER_API_KEY" in done.stderr
    assert "rotate" in done.stderr
    assert "email address or a real name" not in done.stderr
    assert HEX_KEY not in done.stderr + done.stdout
    assert repo.git("rev-parse", "--verify", "-q", "HEAD").returncode != 0


@needs_git
def test_the_hook_finds_python_on_path_by_itself(repo):
    del repo.env["PIPPA_HOOK_PYTHON"]
    repo.env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), repo.env.get("PATH", "")])
    done = repo.commit({"app.py": f'WEATHER_API_KEY = "{HEX_KEY}"' + chr(10)})
    assert done.returncode != 0
    assert "app.py:1: a key-like value given to WEATHER_API_KEY" in done.stderr


@needs_git
def test_reading_the_key_from_the_environment_goes_through(repo):
    done = repo.commit({"app.py": 'import os\nkey = os.environ["WEATHER_API_KEY"]\n',
                        ".env.example": "WEATHER_API_KEY=\n"})
    assert done.returncode == 0, done.stderr


@needs_git
def test_a_test_value_marked_with_the_pragma_goes_through(repo):
    line = f'FIXTURE_TOKEN = "{HEX_KEY}"  # pragma: allowlist secret\n'
    done = repo.commit({"test_x.py": line})
    assert done.returncode == 0, done.stderr


@needs_git
def test_the_pragma_never_lets_a_providers_key_through(repo):
    line = f'FIXTURE = "{AWS_LIKE}"  # pragma: allowlist secret\n'
    done = repo.commit({"test_x.py": line})
    assert done.returncode != 0
    assert "test_x.py:1: an AWS access key id" in done.stderr
    assert AWS_LIKE not in done.stderr + done.stdout


@needs_git
def test_a_key_in_a_commented_line_of_env_example_is_stopped(repo):
    """The template's `.env.example` has `# OPENWEATHER_API_KEY=`; filling
    it in without taking the `#` off must not commit the key."""
    done = repo.commit({".env.example": f"# What the app reads.\n# OPENWEATHER_API_KEY={HEX_KEY}\n"})
    assert done.returncode != 0
    assert ".env.example:2: a value for OPENWEATHER_API_KEY" in done.stderr
    assert HEX_KEY not in done.stderr + done.stdout
    done = repo.commit({".env.example": f"# token {AWS_LIKE}\n"})
    assert done.returncode != 0
    assert ".env.example:1: an AWS access key id" in done.stderr


@needs_git
def test_a_dot_env_file_is_stopped(repo):
    done = repo.commit({".env": "WEATHER_API_KEY=test-key-000000000000000000\n"})
    assert done.returncode != 0
    assert ".env: an environment file" in done.stderr


@needs_git
def test_without_python_the_providers_formats_are_still_stopped(repo):
    repo.env["PIPPA_HOOK_PYTHON"] = "none"
    done = repo.commit({"notes.md": f"one\nkey {AWS_LIKE}\n"})
    assert done.returncode != 0
    assert "notes.md:2: a provider's key format" in done.stderr
    assert "Python was not found" in done.stderr
    assert AWS_LIKE not in done.stderr + done.stdout


@needs_git
def test_without_python_placeholders_go_through(repo):
    repo.env["PIPPA_HOOK_PYTHON"] = "none"
    text = "AKIA" + "X" * 16 + "\n" + "AKIA" + "IOSFODNN7" + "EXAMPLE" + "\n"
    done = repo.commit({"notes.md": text})
    assert done.returncode == 0, done.stderr


@needs_git
def test_without_python_the_pragma_does_not_let_a_providers_key_through(repo):
    repo.env["PIPPA_HOOK_PYTHON"] = "none"
    done = repo.commit({"notes.md": f"x\n{AWS_LIKE} # pragma: allowlist secret\n"})
    assert done.returncode != 0
    assert "notes.md:2: a provider's key format" in done.stderr


@needs_git
def test_without_python_a_dot_env_file_is_still_stopped(repo):
    repo.env["PIPPA_HOOK_PYTHON"] = "none"
    done = repo.commit({"config/.env.local": "X=1\n", ".env.example": "WEATHER_API_KEY=\n"})
    assert done.returncode != 0
    assert "config/.env.local: a file that holds keys" in done.stderr
    assert ".env.example" not in done.stderr
