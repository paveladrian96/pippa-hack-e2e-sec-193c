"""Tests for scripts/set_app_id.py and the workflow that runs it.

NOT a test of your app, and not a file you need to touch. It covers the setup
step that fills in your app id when the repository is made, which already ran
long before you read this. It ships with the template so that a change to the
rule is tested in every repository that keeps a copy of the step.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check  # noqa: E402
import set_app_id  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = """\
manifest_version: 1
app_author_name: ""

app:
  # The id comment, which mentions hack.your_app_name_here on purpose.
  id: hack.your_app_name_here
  name: Days Until

outcomes:
  - id: days.until
"""


def test_the_id_comes_from_the_repository_name():
    cases = {
        "Pippa-Labs/pippa-hack-tide-times": "hack.tide_times",
        "Pippa-Labs/pippa-hack-splitthebill": "hack.splitthebill",
        "Pippa-Labs/pippa-hack-app-3f9a-2": "hack.app_3f9a_2",
        "pippa-labs/pippa-hack-grid-carbon": "hack.grid_carbon",
    }
    for repository, app_id in cases.items():
        assert set_app_id.app_id_for(repository) == app_id, repository


def test_it_agrees_with_the_check_that_runs_on_every_push():
    for name in ("pippa-hack-tide-times", "pippa-hack-x", "pippa-hack-a1-b2-c3"):
        assert set_app_id.app_id_for(f"Pippa-Labs/{name}") == check.expected_app_id(name)


def test_nothing_that_is_not_a_builder_repository_gets_an_id():
    for repository in (
        "Pippa-Labs/pippa-hack-template",          # the templates keep the placeholder
        "Pippa-Labs/pippa-hack-template-public",
        "somebody/pippa-hack-tide-times",          # a fork
        "Pippa-Labs/tide-times",                   # not a builder repository
        "Pippa-Labs/pippa-hack-Tide-Times",        # names the publisher refuses
        "Pippa-Labs/pippa-hack-tide_times",
        "Pippa-Labs/pippa-hack--tide",
        "Pippa-Labs/pippa-hack-",
        "pippa-hack-tide-times",
        "",
    ):
        assert set_app_id.app_id_for(repository) is None, repository


def test_only_the_placeholder_line_changes():
    updated = set_app_id.with_app_id(MANIFEST, "hack.tide_times")
    assert updated == MANIFEST.replace(
        "  id: hack.your_app_name_here\n", "  id: hack.tide_times\n",
    )
    assert "  - id: days.until" in updated
    assert "# The id comment, which mentions hack.your_app_name_here" in updated


def test_windows_line_endings_survive():
    crlf = MANIFEST.replace("\n", "\r\n")
    updated = set_app_id.with_app_id(crlf, "hack.tide_times")
    assert updated == crlf.replace("id: hack.your_app_name_here\r\n", "id: hack.tide_times\r\n")


def test_it_refuses_to_guess_between_two_placeholders():
    twice = MANIFEST + "  id: hack.your_app_name_here\n"
    assert set_app_id.with_app_id(twice, "hack.tide_times") is None


def test_running_it_sets_the_id_once_and_then_does_nothing(tmp_path, capsys):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_bytes(MANIFEST.encode("utf-8"))
    assert set_app_id.main(["Pippa-Labs/pippa-hack-tide-times", str(manifest)]) == 0
    first = manifest.read_bytes()
    assert b"  id: hack.tide_times\n" in first
    assert set_app_id.main(["Pippa-Labs/pippa-hack-tide-times", str(manifest)]) == 0
    assert manifest.read_bytes() == first
    assert "already set" in capsys.readouterr().out


def test_an_id_somebody_already_set_is_left_alone(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    text = MANIFEST.replace("id: hack.your_app_name_here", "id: hack.tides")
    manifest.write_text(text, encoding="utf-8")
    assert set_app_id.main(["Pippa-Labs/pippa-hack-tide-times", str(manifest)]) == 0
    assert manifest.read_text(encoding="utf-8") == text


def test_a_template_is_left_alone(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    assert set_app_id.main(["Pippa-Labs/pippa-hack-template-public", str(manifest)]) == 0
    assert manifest.read_text(encoding="utf-8") == MANIFEST


def test_the_workflow_never_runs_in_a_template_or_outside_the_org():
    """The guard is the workflow's `if:`, and the templates' own id has to stay
    the placeholder, so it is worth a test of its own."""
    workflow = (ROOT / ".github" / "workflows" / "setup.yml").read_text(encoding="utf-8")
    guard = re.search(r"\n    if: >-\n((?:      .*\n)+)", workflow)
    assert guard, "the job has no `if:` guard"
    condition = " ".join(guard.group(1).split())
    assert "startsWith(github.repository, 'Pippa-Labs/pippa-hack-')" in condition
    assert "github.repository != 'Pippa-Labs/pippa-hack-template'" in condition
    assert "github.repository != 'Pippa-Labs/pippa-hack-template-public'" in condition
    assert "!github.event.repository.is_template" in condition


def test_the_workflow_looks_for_the_placeholder_the_way_the_build_does():
    workflow = (ROOT / ".github" / "workflows" / "setup.yml").read_text(encoding="utf-8")
    assert (
        r"placeholder='^[[:space:]]*id:[[:space:]]*hack\.your_app_name_here[[:space:]]*$'"
        in workflow
    )
    assert 'python3 scripts/set_app_id.py "$GITHUB_REPOSITORY" manifest.yaml' in workflow
