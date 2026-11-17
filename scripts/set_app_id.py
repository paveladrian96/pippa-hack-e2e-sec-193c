"""Fills in `app.id` in manifest.yaml from this repository's name.

NOT A BUILDER TASK, and nothing Claude runs. `.github/workflows/setup.yml` runs
it in the first minute of a new repository's life, so the id the builder
starts with is already the one id this repository can publish:

    Pippa-Labs/pippa-hack-tide-times  ->  hack.tide_times

It changes one line, the placeholder `id: hack.your_app_name_here`, and only
that line, so every comment in manifest.yaml survives. Anything else it leaves
alone: an id somebody already set, a repository that is not a builder
repository, a template. Running it twice changes nothing the second time.

    python scripts/set_app_id.py Pippa-Labs/pippa-hack-tide-times manifest.yaml

Standard library only: the workflow runs it before anything is installed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ORG = "Pippa-Labs"
REPO_PREFIX = "pippa-hack-"
PLACEHOLDER = "hack.your_app_name_here"
#: The names a builder repository can have, the same rule the publisher
#: applies: lowercase letters and digits, in words joined by single hyphens.
REPO_NAME = re.compile(r"^pippa-hack-[a-z0-9]+(-[a-z0-9]+)*$")
#: The two templates every builder repository is made from. Their own id stays
#: the placeholder for ever: it is what every new repository starts with.
TEMPLATES = frozenset({"pippa-hack-template", "pippa-hack-template-public"})
#: The placeholder line, as the build recognises it ("Nothing to publish yet").
PLACEHOLDER_LINE = re.compile(
    r"^([ \t]*id:[ \t]*)hack\.your_app_name_here([ \t]*\r?)$", re.MULTILINE,
)


def app_id_for(repository: str) -> str | None:
    """`Pippa-Labs/pippa-hack-tide-times` -> `hack.tide_times`.

    None for anything that is not a builder repository: another owner (a
    fork), a template, or a name the publisher would refuse.
    """
    owner, _, name = repository.strip().partition("/")
    if owner.lower() != ORG.lower() or name in TEMPLATES or not REPO_NAME.match(name):
        return None
    return "hack." + name[len(REPO_PREFIX):].replace("-", "_")


def placeholder_lines(text: str) -> int:
    """How many lines of `text` are the placeholder id."""
    return len(PLACEHOLDER_LINE.findall(text))


def with_app_id(text: str, app_id: str) -> str | None:
    """`text` with the placeholder replaced by `app_id`, or None if there is no
    single placeholder line to replace."""
    if placeholder_lines(text) != 1:
        return None
    return PLACEHOLDER_LINE.sub(lambda m: f"{m.group(1)}{app_id}{m.group(2)}", text)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: set_app_id.py <owner/repository> <manifest.yaml>", file=sys.stderr)
        return 2
    repository, manifest = argv[0], Path(argv[1])
    app_id = app_id_for(repository)
    if app_id is None:
        print(f"{repository} is not a builder repository; app.id left as it is.")
        return 0
    try:
        text = manifest.read_bytes().decode("utf-8")
    except OSError as exc:
        print(f"::warning::{manifest} could not be read ({exc}); app.id left as it is.")
        return 0
    if placeholder_lines(text) == 0:
        print("app.id is already set; nothing to do.")
        return 0
    updated = with_app_id(text, app_id)
    if updated is None:
        print(f"::warning::{manifest} does not have exactly one `id: {PLACEHOLDER}` "
              "line; app.id left as it is.")
        return 0
    manifest.write_bytes(updated.encode("utf-8"))
    print(f"app.id set to {app_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
