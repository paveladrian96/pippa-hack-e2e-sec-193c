"""Tests for the template's own docs about API keys: that they say what Pippa
really does, and that they carry the rules that keep a key with its provider.

NOT a test of your app, and it never runs in your repository: it checks the
template's docs, and in a builder's repository the docs are theirs to change.
It runs only in Pippa-Labs/pippa-hack-template and pippa-hack-template-public
(or anywhere with PIPPA_TEMPLATE_DOCS_TESTS=1).

The sentences below are Pippa's own, copied from pippa_agentapp_runtime 0.6.0,
which is what a builder or the person asking actually reads. If the runtime
changes one, change it here and in every doc that quotes it.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

TEMPLATES = frozenset({"pippa-hack-template", "pippa-hack-template-public"})


def _template_checkout() -> bool:
    """True in a clone of one of the two templates (by its `origin`)."""
    if os.environ.get("PIPPA_TEMPLATE_DOCS_TESTS") == "1":
        return True
    try:
        url = subprocess.run(
            ["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False
    name = re.split(r"[/:]", url.rstrip("/"))[-1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name in TEMPLATES


pytestmark = pytest.mark.skipif(
    not _template_checkout(),
    reason="checks the template's own docs; a builder's docs are theirs to change",
)

# ── Pippa's own sentences (pippa_agentapp_runtime 0.6.0) ─────────────────────

#: rate_limits.MINUTE_SENTENCE and DAY_SENTENCE.
RATE_MINUTE = "This app has had a lot of requests in the last minute; try again in a minute."
RATE_DAY = "This app has had a lot of requests today; try again tomorrow."
#: app_secrets.not_ready_sentence(["OPENWEATHER_API_KEY"]).
NOT_READY = "This app isn't ready yet: its builder still has to add OPENWEATHER_API_KEY."
#: app_secrets.publish_warning(["OPENWEATHER_API_KEY"]).
PUBLISH_WARNING = (
    "Published, but it can't run until you add OPENWEATHER_API_KEY in Created by me."
)
#: service.SECRETS_UNAVAILABLE_SENTENCE.
UNAVAILABLE = "This app can't run right now. Try again in a little while."
#: rate_limits.RATE_LIMITS_UNAVAILABLE_SENTENCE (503 rate_limits_unavailable):
#: a call that would carry the builder's keys and cannot be counted.
UNCOUNTED = (
    "This app can't run right now because Pippa can't count its requests. "
    "Try again in a little while."
)
#: app_secrets.PUBLISHED_BEFORE_HANDOVER_SENTENCE (502
#: published_before_handover): a version published under another owner or
#: repository than the app's link names now.
HANDOVER = (
    "This version was published before the app changed hands; its builder "
    "must publish again."
)

#: Every sentence a person can be shown when Pippa does not run an app that
#: declares keys, or that a builder sees for one.
SENTENCES = (PUBLISH_WARNING, NOT_READY, UNAVAILABLE, UNCOUNTED, HANDOVER,
             RATE_MINUTE, RATE_DAY)

#: rate_limits.Limits' defaults: per (app, agent) 20 a minute and 300 a day;
#: per app 120 a minute and 3000 a day.
PER_PERSON = re.compile(r"20 times a minute and 300 (?:times )?a day")
PER_APP = re.compile(r"120 (?:calls |times )?a minute and 3,000 (?:times )?a day")
#: The first two are per agent (`body.agent_id`), not per person.
PER_AGENT = ("each Pippa agent", "somebody with several")


# ── Reading the docs ─────────────────────────────────────────────────────────


def _plain(text: str) -> str:
    """Text as a reader sees it: no tags, entities, `*` or backticks, and
    every run of white space one space."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def _section(relative: str, start: str, end: str) -> str:
    """The part of a file from the line `start` up to the next line matching
    `end`, as plain text."""
    text = (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")
    begin = text.find(start)
    assert begin >= 0, f"{relative} has no {start!r} section"
    rest = text[begin + len(start):]
    stop = re.search(end, rest, flags=re.MULTILINE)
    return _plain(rest[: stop.start()] if stop else rest)


#: Line breaks around a heading, so that only the heading itself matches.
NL = chr(10)


def using_api_keys() -> str:
    return _section("docs/API_APPS.md", f"{NL}## Using API keys{NL}", r"^## ")


def claude_rules() -> str:
    return _section("CLAUDE.md", f"{NL}## API keys{NL}", r"^## ")


def guide() -> str:
    return _section("docs/builder-guide.html", "<h2>If your app needs an API key</h2>",
                    r"<h2>If something goes wrong</h2>")


def readme() -> str:
    return _section("README.md", f"{NL}## If your app needs an API key{NL}", r"^## If something")


def troubleshooting() -> str:
    return _section("docs/TROUBLESHOOTING.md", f"{NL}# API keys{NL}", r"^# Who can see it")


def _every_doc() -> dict[str, str]:
    return {
        "docs/API_APPS.md": _plain((ROOT / "docs/API_APPS.md").read_text(encoding="utf-8")),
        "CLAUDE.md": _plain((ROOT / "CLAUDE.md").read_text(encoding="utf-8")),
        "README.md": _plain((ROOT / "README.md").read_text(encoding="utf-8")),
        "docs/builder-guide.html": _plain(
            (ROOT / "docs/builder-guide.html").read_text(encoding="utf-8")),
        "docs/TROUBLESHOOTING.md": _plain(
            (ROOT / "docs/TROUBLESHOOTING.md").read_text(encoding="utf-8")),
    }


def _missing(text: str, phrases) -> list[str]:
    return [p for p in phrases if (p.search(text) is None if isinstance(p, re.Pattern)
                                   else p not in text)]


# ── What Pippa really does (T3) ──────────────────────────────────────────────


def test_using_api_keys_quotes_pippas_own_sentences():
    missing = _missing(using_api_keys(), SENTENCES)
    assert not missing, f'docs/API_APPS.md, "Using API keys", does not quote: {missing}'


def test_troubleshooting_has_an_entry_for_each_of_pippas_sentences():
    raw = (ROOT / "docs/TROUBLESHOOTING.md").read_text(encoding="utf-8")
    headings = {line[3:].strip().strip("`") for line in raw.splitlines()
                if line.startswith("## ")}
    missing = [s for s in SENTENCES if s not in headings]
    assert not missing, f"docs/TROUBLESHOOTING.md has no entry headed: {missing}"


@pytest.mark.parametrize("name, read", [
    ("docs/API_APPS.md", using_api_keys),
    ("README.md", readme),
    ("docs/builder-guide.html", guide),
    ("docs/TROUBLESHOOTING.md", troubleshooting),
])
def test_the_limits_are_pippas_defaults(name, read):
    missing = _missing(read(), [PER_PERSON, PER_APP])
    assert not missing, f"{name} does not give Pippa's default call limits: {missing}"


@pytest.mark.parametrize("name, read", [
    ("docs/API_APPS.md", using_api_keys),
    ("README.md", readme),
    ("docs/builder-guide.html", guide),
    ("docs/TROUBLESHOOTING.md", troubleshooting),
])
def test_the_first_limits_are_per_agent_not_per_person(name, read):
    # Counted per (app, agent): somebody with several Pippa agents gets a
    # share for each, so "each person" promises the builder too little.
    text = read()
    missing = _missing(text, PER_AGENT)
    assert not missing, f"{name} does not say the limits are per agent: {missing}"
    assert "for each person" not in text and "each person can call" not in text, name


def test_only_the_owner_sets_a_key_and_only_after_the_push_that_declares_it():
    assert not _missing(using_api_keys(), [
        "Only the app's owner can do this: the Pippa account this repository was created for.",
        "Push the version that declares the key first: it publishes without the value.",
        "A key is listed there once a published version declares it.",
    ])
    assert "Only the app's owner can set its keys" in claude_rules()
    for name, read in (("README.md", readme), ("docs/builder-guide.html", guide)):
        assert "listed there once Claude has pushed the version that declares it, and "\
               "only for you" in read(), name
    assert "There is no Keys section on my app's card" in troubleshooting()


def test_no_doc_says_a_key_can_be_set_before_the_push_that_declares_it():
    # Pippa's own API takes one, but the Keys page lists only declared keys,
    # so a builder following this could not do it.
    for name, text in _every_doc().items():
        assert "set a key before the first push" not in text, name


def test_a_version_from_before_a_change_of_owner_gets_no_keys():
    assert "A version published before the change gets no keys" in using_api_keys()
    assert "Versions published before the change get no keys" in claude_rules()
    assert "versions published before the change get no keys" in troubleshooting()
    # It is not "missing": Pippa refuses it before it looks at the values.
    assert "published before the app moved to your account" not in troubleshooting()


def test_renaming_or_relinking_the_repository_also_deletes_the_keys():
    # service.link_repo wipes on `owner_changed` and `link_renamed`.
    for name, read in (("docs/API_APPS.md", using_api_keys), ("CLAUDE.md", claude_rules),
                       ("docs/TROUBLESHOOTING.md", troubleshooting)):
        missing = _missing(read(), [re.compile(r"re-link(?:s|ed) its repository"),
                                    re.compile(r"repository (?:is|was) renamed")])
        assert not missing, f"{name} does not say: {missing}"


# ── Keeping the key with its provider (T2) ───────────────────────────────────

#: For each doc, the sentence that carries each of the four rules.
RULES = {
    "docs/API_APPS.md": (using_api_keys, {
        "where it is sent": "Never let the question choose where the key is sent.",
        "no model or tool": "Never give a model or a tool a way to read the environment.",
        "never in any form": "Never return, print or log a key, in any form.",
        "only exact copies are hidden": "It does not recognise the key in any other form",
        "provider errors": "Never pass on a provider's error.",
    }),
    "CLAUDE.md": (claude_rules, {
        "where it is sent": "Nothing from the question, or from any other input, may "
                            "choose the host, the URL, a redirect to follow or the "
                            "header the key is sent in",
        "no model or tool": "Never give a model or a tool a way to read the environment.",
        "never in any form": "Never return, print or log a key, in any form",
        "only exact copies are hidden": "Pippa hides an exact or URL-encoded copy of a key "
                                        "in what the app returns and prints, and nothing else",
        "provider errors": "Never pass on a provider's error text, its response body or "
                           "the request URL: some providers repeat the key in them.",
    }),
    "docs/builder-guide.html": (guide, {
        "where it is sent": "nothing a person types can choose where it goes",
        "no model or tool": "never let an AI model your app calls, or any tool it is "
                            "given, read the key",
        "never in any form": "never hand the key back, print it or log it, in any form",
        "only exact copies are hidden": "Pippa hides an exact copy of the key from your "
                                        "app's answers, but not a changed one",
        "provider errors": "never pass on a provider's own error message, which can "
                           "repeat the key",
    }),
    "README.md": (readme, {
        "where it is sent": "nothing a person types can choose where it goes",
        "no model or tool": "never to let an AI model it calls read it",
        "never in any form": "never to hand it back, print it",
        "only exact copies are hidden": "Pippa hides an exact copy of the key from your "
                                        "app's answers, but not a changed one",
        "provider errors": "pass on a provider's error message that repeats it",
    }),
}


@pytest.mark.parametrize("name", sorted(RULES))
def test_the_key_stays_between_the_app_and_its_provider(name):
    read, rules = RULES[name]
    text = read()
    missing = [rule for rule, sentence in rules.items() if sentence not in text]
    assert not missing, f"{name} no longer says: {missing}"


def test_the_example_sends_the_key_to_a_fixed_address():
    text = using_api_keys()
    assert 'self._fetch("https://api.openweathermap.org/data/2.5/weather?" + query)' in text
    assert "nobody can choose where the key goes" in text


def test_no_doc_promises_more_than_pippa_hides():
    for name, text in _every_doc().items():
        assert "nothing in your repository can reveal them" not in text, name
        assert "Pippa hides the key if it sees it" not in text, name


# ── A key in a header stays off a redirect ───────────────────────────────────

#: A key-carrying header given to `Request(headers={...})` or `add_header()`:
#: urllib sends both on to whatever host a redirect names.
HEADER_THAT_FOLLOWS_A_REDIRECT = re.compile(
    r"""(?:headers\s*=\s*\{[^}]*|\badd_header\(\s*)["'](?:Authorization|[\w-]*api[_-]?key[\w-]*)["']""",
    re.IGNORECASE,
)


def test_a_header_key_is_attached_so_it_does_not_follow_a_redirect():
    for name, read in (("docs/API_APPS.md", using_api_keys), ("CLAUDE.md", claude_rules)):
        missing = _missing(read(), [
            'add_unredirected_header("Authorization"' if name == "docs/API_APPS.md"
            else "request.add_unredirected_header(name, value), never in "
                 "Request(headers=...) or add_header()",
            "Or refuse redirects",
        ])
        assert not missing, f"{name} no longer says: {missing}"


def test_no_example_puts_a_key_in_a_header_that_follows_a_redirect():
    for name in ("CLAUDE.md", "README.md", "docs/API_APPS.md", "docs/IDEAS.md",
                 "docs/TROUBLESHOOTING.md", "docs/builder-guide.html"):
        raw = (ROOT / name).read_text(encoding="utf-8")
        found = [m.group(0) for m in HEADER_THAT_FOLLOWS_A_REDIRECT.finditer(raw)]
        assert not found, (
            f"{name} sends a key in a header that urllib passes on to a redirect: "
            f"{found}. Use add_unredirected_header instead."
        )


def test_the_search_rule_keeps_claude_out_of_env():
    rules = claude_rules()
    missing = _missing(rules, [
        "Search the repository only with the Grep tool or git grep.",
        "Never search it from the shell with grep -r, rg -uu, find,",
        "never give a shell command a wildcard that can match .env",
    ])
    assert not missing, f"CLAUDE.md no longer says: {missing}"


# ── .env: the person makes it, never Claude ──────────────────────────────────

#: The one command the person runs to make `.env`: elsewhere, and on Windows.
MAKE_ENV = ("cp .env.example .env", "copy .env.example .env")


def test_claude_gives_the_command_to_make_env_and_never_makes_it():
    # .claude/settings.json denies Edit(./.env), which Claude Code applies to
    # creating the file too, from the shell included (cp is refused). A doc
    # that says Claude may make it sends Claude looking for a way round.
    rules = claude_rules()
    assert not _missing(rules, MAKE_ENV), "CLAUDE.md does not give both commands"
    assert "Never create, copy, move or change .env either: the person makes it." in rules
    assert "Never try another route to make it" in rules
    missing = _missing(using_api_keys(), MAKE_ENV + (
        "Claude gives you that command and never runs it",))
    assert not missing, f'docs/API_APPS.md, "Using API keys", does not say: {missing}'


def test_no_doc_says_claude_can_make_env():
    for name, text in _every_doc().items():
        for phrase in ("Claude can make it", "you may create it", "Claude makes .env"):
            assert phrase not in text, f"{name} still says {phrase!r}"
    for name, read in (("README.md", readme), ("docs/builder-guide.html", guide)):
        text = read()
        if re.search(r"\.env\b", text):  # not os.environ
            assert not _missing(text, MAKE_ENV), f"{name} mentions .env without the command"
