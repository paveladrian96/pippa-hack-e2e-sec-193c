"""Tests for scripts/check_secrets.py, the check that stops a key from being
committed.

NOT a test of your app, and not a file you need to touch. `pytest` finds it
because `testpaths` in pytest.ini is the whole repository.

No key is written out in this file. Every value that must be caught is put
together while the test runs (`"AKIA" + ...`), so this file never looks like
a leak to GitHub, to the build's own scanner, or to the check it tests.
"""

from __future__ import annotations

import random
import re
import shutil
import string
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_secrets as cs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".githooks" / "pre-commit"

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def rand(length: int, alphabet: str = string.ascii_letters + string.digits, seed: int = 7) -> str:
    """A random-looking value, the same on every run, made here rather than
    written out."""
    chooser = random.Random(seed)
    mixed = any(c.isdigit() for c in alphabet) and any(c.isalpha() for c in alphabet)
    for _ in range(1000):
        value = "".join(chooser.choice(alphabet) for _ in range(length))
        # Mixed, as real keys are, and never by chance a placeholder word.
        if mixed and not (any(c.isdigit() for c in value) and any(c.isalpha() for c in value)):
            continue
        if not cs.is_placeholder(value):
            return value
    raise AssertionError("no random value could be made")


HEX = "0123456789abcdef"

#: One sample per provider format, each built at run time.
PROVIDER_SAMPLES = {
    "an AWS access key id": "AKIA" + rand(16, string.ascii_uppercase + string.digits),
    "a GitHub token": "gh" + "p_" + rand(36),
    "a Slack token": "xo" + "xb-" + rand(12, string.digits) + "-" + rand(24),
    "an Anthropic API key": "sk-" + "ant-" + "api03-" + rand(40),
    "a Google API key": "AI" + "za" + rand(35),
    "a SendGrid API key": "SG." + rand(22) + "." + rand(43),
    "a Hugging Face token": "h" + "f_" + rand(34),
    "a Stripe key": "sk" + "_live_" + rand(24),
}


def kinds(line: str, allowed=frozenset()) -> list[str]:
    return cs.scan_line(line, allowed)


# ── Provider formats ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", sorted(PROVIDER_SAMPLES))
def test_each_providers_format_is_caught(kind):
    value = PROVIDER_SAMPLES[kind]
    assert kind in kinds(f'KEY = "{value}"')
    assert kind in kinds(f"export THING={value}")
    assert kind in kinds(f"see {value} here")


def test_a_github_fine_grained_token_and_an_openai_style_key_are_caught():
    assert "a GitHub token" in kinds("t = '" + "github_" + "pat_" + rand(60, string.ascii_letters + "_" + string.digits) + "'")
    assert "a secret key (sk-...)" in kinds('client = Client("' + "sk-" + "proj-" + rand(48) + '")')


def test_a_private_key_block_is_caught():
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    assert "a private key" in kinds(header)
    assert "a private key" in kinds("-----BEGIN " + "OPENSSH PRIVATE KEY-----")
    assert "a private key" in kinds("-----BEGIN " + "PRIVATE KEY-----")
    assert kinds("-----BEGIN " + "PUBLIC KEY-----") == []


def test_a_key_inside_a_longer_word_is_not_a_provider_key():
    assert kinds("XAKIA" + rand(16, string.ascii_uppercase + string.digits)) == []


# ── Placeholders and the allowlist ───────────────────────────────────────────

def test_obvious_placeholders_are_let_through():
    for line in (
        'AWS_KEY = "' + "AKIA" + "X" * 16 + '"',
        'AWS_KEY = "' + "AKIA" + "IOSFODNN7" + "EXAMPLE" + '"',
        'OPENWEATHER_API_KEY = "your-key-here-0000000"',
        'api_key = "<paste your key here 123>"',
        'API_KEY = "changeme-changeme-123456"',
        'SECRET_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxx"',
        "url = 'https://api.nasa.gov/planetary/apod?api_key=" + "DEMO_KEY" + "'",
        'NASA_API_KEY = "' + "DEMO_KEY" + '"',
        "token: ${GITHUB_TOKEN_FROM_THE_ENVIRONMENT_1}",
    ):
        assert kinds(line) == [], line


def test_the_pragma_lets_through_a_value_that_only_looks_like_a_key():
    value = rand(32, HEX)
    for line in (
        f'FIXTURE_TOKEN = "{value}"',
        f'headers = {{"Authorization": "Bearer {rand(40)}"}}',
        f"url = 'https://api.example.com/v1?api_key={value}'",
    ):
        assert kinds(line) != [], line
        assert kinds(line + "  # pragma: allowlist secret") == [], line


@pytest.mark.parametrize("kind", sorted(PROVIDER_SAMPLES))
def test_the_pragma_never_lets_through_a_providers_format(kind):
    """A comment on the line must not be enough to commit a real key: no test
    needs one in a provider's own format."""
    value = PROVIDER_SAMPLES[kind]
    assert kind in kinds(f'FIXTURE = "{value}"  # pragma: allowlist secret')
    assert kind in kinds(f"# pragma: allowlist secret {value}")


def test_the_pragma_never_lets_through_a_private_key_or_an_sk_key():
    assert "a private key" in kinds("-----BEGIN " + "RSA PRIVATE KEY----- # pragma: allowlist secret")
    sk = "sk-" + "proj-" + rand(48)
    assert "a secret key (sk-...)" in kinds(f'KEY = "{sk}"  # pragma: allowlist secret')


def test_values_listed_in_env_example_are_allowed_everywhere():
    allowed, findings = cs.env_example("WEATHER_API_KEY=set-it-in-dot-env-1\n")
    assert findings == []
    assert "set-it-in-dot-env-1" in allowed
    assert kinds('WEATHER_API_KEY = "set-it-in-dot-env-1"', allowed) == []


def test_env_example_holds_names_only_and_a_real_looking_value_is_reported():
    real = rand(32, HEX)
    text = (
        "# What the app needs. Values go in .env, never here.\n"
        "WEATHER_API_KEY=\n"
        f"OTHER_KEY={real}\n"
        "THIRD_KEY='' \n"
    )
    allowed, findings = cs.env_example(text)
    assert [(f.line, f.kind) for f in findings] == [
        (3, "a value for OTHER_KEY that looks like a real key (.env.example holds names only)")
    ]
    assert real not in allowed
    assert cs.scan_text(".env.example", text) == findings


def test_a_commented_line_in_env_example_is_searched_too():
    """The template ships `# OPENWEATHER_API_KEY=`: filling it in without
    taking the `#` off still commits the key."""
    real = rand(32, HEX)
    github = PROVIDER_SAMPLES["a GitHub token"]
    text = (
        "# OpenWeather key, used to look up the forecast.\n"
        f"# OPENWEATHER_API_KEY={real}\n"
        f"# token {github}\n"
        f"#   export OTHER_KEY='{real}'\n"
        f"# see https://api.example.com/v1?appid={real}\n"
        "# OPENWEATHER_API_KEY=\n"
        "# NASA_API_KEY=DEMO_KEY\n"
        "# WEATHER_API_KEY=your-key-here\n"
    )
    allowed, findings = cs.env_example(text)
    assert [(f.line, f.kind) for f in findings] == [
        (2, "a value for OPENWEATHER_API_KEY that looks like a real key (.env.example holds names only)"),
        (3, "a GitHub token"),
        (4, "a value for OTHER_KEY that looks like a real key (.env.example holds names only)"),
        (5, "a key in a URL (appid=)"),
    ]
    assert allowed == frozenset()  # a commented value is not allowed elsewhere
    assert cs.scan_text("config/.env.example", text) == [
        cs.Finding("config/.env.example", f.line, f.kind) for f in findings
    ]


def test_a_provider_key_in_env_example_is_reported_even_with_the_pragma():
    aws = PROVIDER_SAMPLES["an AWS access key id"]
    text = (f"AWS_THING={aws}  # pragma: allowlist secret\n"
            f"# {aws} # pragma: allowlist secret\n"
            f"HEX_KEY={rand(32, HEX)}  # pragma: allowlist secret\n")
    assert [f.line for f in cs.env_example(text)[1]] == [1, 2]


def test_the_templates_own_env_example_is_clean():
    example = ROOT / ".env.example"
    allowed, findings = cs.env_example(example.read_text(encoding="utf-8"))
    assert findings == []


# ── The name a finding prints ────────────────────────────────────────────────

def test_a_finding_never_prints_value_characters_that_run_on_from_the_name():
    value = rand(32, HEX)
    for line, shown in (
        (f'cfg.token_{value} = "{value}"', "cfg.token"),
        (f'TOKEN{value} = "{value}"', "TOKEN"),
        (f'x{value}_key = "{value}"', "key"),
        (f"export API_KEY_{value}={value}", "API_KEY"),
        (f'"{"a" * 50}_secret": "{value}"', "secret"),
    ):
        found = kinds(line)
        assert found == [f"a key-like value given to {shown}"], line
        assert value[:8] not in found[0]


def test_an_ordinary_name_is_printed_whole():
    value = rand(32, HEX)
    for name in ("OPENWEATHER_API_KEY", "giphy_api_key", "apiKey", "client_secret",
                 "DB_PASSWORD", "cfg.auth_token"):
        assert kinds(f'{name} = "{value}"') == [f"a key-like value given to {name}"]
    assert cs.shown_name("API_KEY_NAME") == "API_KEY"
    assert cs.shown_name("tokens") == "token"


# ── Keys recognised by their surroundings ────────────────────────────────────

def test_a_random_value_given_to_a_key_name_is_caught_in_every_common_form():
    value = rand(32, HEX)
    for line in (
        f'OPENWEATHER_API_KEY = "{value}"',
        f"giphy_api_key = '{value}'",
        f'    "apiKey": "{value}",',
        f'client_secret: "{value}"',
        f"DB_PASSWORD={value}",
        f"export SERVICE_TOKEN={value}",
        f"api_key: {value}  # from the dashboard",
        f'params = {{"appid": "{value}"}}',
    ):
        found = kinds(line)
        assert found and found[0].startswith("a key-like value given to "), line


def test_names_and_code_are_not_keys():
    for line in (
        'OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]',
        'key = os.environ.get("OPENWEATHER_API_KEY", "")',
        'API_KEY_NAME = "OPENWEATHER_API_KEY"',
        'AUTHOR_NAME_KEY = "app_author_name"',
        'cache_key = f"{place}-{day}-forecast-v2"',
        'token = "value-of-some-thing-v2-final"',
        'key_file = "src/keys/loader_v2.py"',
        "secret_doc: https://example.com/docs/keys/v2/setup",
        'sort_key = "name"',
        "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
        'app_author_name: "Tidewatcher"',
    ):
        assert kinds(line) == [], line


def test_a_key_in_a_url_is_caught_but_a_variable_is_not():
    value = rand(32, HEX)
    assert kinds(f"https://api.openweathermap.org/data/2.5/weather?q=Leeds&appid={value}") == [
        "a key in a URL (appid=)"
    ]
    assert kinds(f'url = "https://api.example.com/v1?api_key={value}&q=x"')[-1] == (
        "a key in a URL (api_key=)"
    )
    assert kinds('url = f"https://api.example.com/v1?api_key={key}&q=x"') == []
    assert kinds('url = base + "?" + urlencode({"appid": key, "q": place})') == []


def test_a_bearer_or_authorization_literal_is_caught_but_not_a_variable():
    value = rand(40)
    assert "a Bearer token" in kinds(f'headers = {{"Authorization": "Bearer {value}"}}')
    assert "an Authorization header value" in kinds(f'"Authorization": "Token {value}"')
    assert kinds('headers = {"Authorization": f"Bearer {token}"}') == []
    assert kinds('headers = {"Authorization": "Bearer " + token}') == []
    assert kinds("Send the key as a Bearer token in the Authorization header.") == []


# ── Never the value ──────────────────────────────────────────────────────────

def test_what_it_reports_never_contains_the_value():
    lines = [f'K{i} = "{v}"' for i, v in enumerate(PROVIDER_SAMPLES.values())]
    lines.append(f'MY_API_KEY = "{rand(32, HEX)}"')
    findings = cs.scan_text("app.py", "\n".join(lines))
    assert len(findings) == len(lines)
    printed = cs.report(findings) + "\n".join(f.kind for f in findings)
    for value in list(PROVIDER_SAMPLES.values()) + [rand(32, HEX)]:
        assert value not in printed
        assert value[4:12] not in printed


# ── Files that hold keys by their nature ─────────────────────────────────────

def test_files_that_hold_keys_are_named():
    for path in (".env", ".env.local", ".env.production", "config/prod.env", "server.pem",
                 "tls.key", "id_rsa", "id_ed25519", "credentials.json",
                 "credentials-prod.json", "client_secret.json", ".npmrc", "keystore.p12"):
        assert cs.key_file_kind(path), path
    for path in (".env.example", "id_rsa.pub", "environment.py", "keys.py", "app.py",
                 "docs/API_APPS.md", "credentials.md", "manifest.yaml"):
        assert cs.key_file_kind(path) is None, path


def test_a_key_file_is_reported_whatever_it_contains_and_binary_files_are_skipped():
    value = PROVIDER_SAMPLES["an AWS access key id"]
    findings = cs.scan_blobs([
        (".env", b"NOTHING=here\n"),
        ("logo.png", b"\x89PNG\0\0" + value.encode()),
        ("big.txt", (value + "\n").encode() * (cs.SCAN_LIMIT_BYTES // 10)),
        ("notes.md", f"x\n{value}\n".encode()),
    ])
    assert [(f.path, f.line) for f in findings] == [(".env", 0), ("notes.md", 2)]


# ── The hook's copy of the provider formats ──────────────────────────────────

def test_the_hook_falls_back_to_exactly_these_formats():
    text = HOOK.read_text(encoding="utf-8")
    copied = re.search(r"^secret_re='([^']*)'$", text, re.MULTILINE)
    assert copied and copied.group(1) == cs.HOOK_PATTERN


def test_every_provider_sample_is_matched_by_the_hook_pattern_in_python():
    pattern = re.compile(cs.HOOK_PATTERN)
    for kind, value in PROVIDER_SAMPLES.items():
        assert pattern.search(value), kind


@pytest.mark.skipif(shutil.which("grep") is None, reason="grep is not installed")
def test_the_hook_pattern_is_a_valid_grep_pattern_that_finds_the_samples(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_text("nothing here\n" + "\n".join(PROVIDER_SAMPLES.values()) + "\n",
                      encoding="utf-8")
    done = subprocess.run(["grep", "-cE", cs.HOOK_PATTERN, str(sample)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(len(PROVIDER_SAMPLES))


# ── A real repository ────────────────────────────────────────────────────────

def git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.name=Tidewatcher",
         "-c", "user.email=12345+tidewatcher@users.noreply.github.com",
         "-c", "core.autocrlf=false", *args],
        cwd=path, capture_output=True, text=True, timeout=60,
    )


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    assert git(path, "init", "-q").returncode == 0
    return path


@needs_git
def test_the_tree_scan_reads_tracked_files_only(repo):
    value = rand(32, HEX)
    (repo / "app.py").write_text(f'API_KEY = "{value}"\n', encoding="utf-8")
    (repo / ".env").write_text(f"API_KEY={value}\n", encoding="utf-8")  # untracked: fine
    git(repo, "add", "app.py")
    findings = cs.scan_tree(repo)
    assert [(f.path, f.line) for f in findings] == [("app.py", 1)]

    git(repo, "add", "-f", ".env")
    assert [(f.path, f.line) for f in cs.scan_tree(repo)] == [(".env", 0), ("app.py", 1)]


@needs_git
def test_the_staged_copy_is_what_counts(repo):
    value = rand(32, HEX)
    (repo / "app.py").write_text(f'API_KEY = "{value}"\n', encoding="utf-8")
    git(repo, "add", "app.py")
    (repo / "app.py").write_text('API_KEY = os.environ["API_KEY"]\n', encoding="utf-8")
    assert [(f.path, f.line) for f in cs.scan_staged(repo)] == [("app.py", 1)]
    git(repo, "add", "app.py")
    assert cs.scan_staged(repo) == []


@needs_git
def test_the_command_exits_1_and_never_prints_the_value(repo):
    value = rand(32, HEX)
    (repo / "weather.py").write_text(f'\n\nOPENWEATHER_API_KEY = "{value}"\n', encoding="utf-8")
    git(repo, "add", "weather.py")
    script = str(Path(cs.__file__).resolve())
    done = subprocess.run([sys.executable, script, "--staged"], cwd=repo,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "weather.py:3: a key-like value given to OPENWEATHER_API_KEY" in done.stdout
    assert "rotate" in done.stdout
    assert value not in done.stdout + done.stderr

    clean = subprocess.run([sys.executable, script], cwd=repo, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
    assert clean.returncode == 1  # the tree scan finds the same file
    git(repo, "rm", "-q", "--cached", "weather.py")
    clean = subprocess.run([sys.executable, script], cwd=repo, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
    assert clean.returncode == 0, clean.stdout


def test_outside_a_repository_there_is_nothing_to_check(tmp_path):
    assert cs.scan_tree(tmp_path) is None or cs.scan_tree(tmp_path) == []
