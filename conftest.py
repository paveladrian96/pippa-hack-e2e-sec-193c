"""No test may touch the network. This makes that true rather than advised.

(It also skips the app's tests while `app_author_name` in manifest.yaml is
still empty: see `_no_author_name_yet` below.)

The template tells you four times to keep the network out of your tests, and
until now nothing enforced it. A test that really calls the API passes on your
machine, passes in the build, and then fails on a train, in a hotel, or on the
morning the service has an outage — and the failure arrives looking like a bug
in your app rather than a bug in your test.

It is also slow, and it makes your expected numbers change overnight.

So every outbound socket is refused while the suite runs. If a test reaches
for the network it fails immediately, with a message naming the host it tried
to reach and what to do instead.

**You do not need to change anything to benefit from this.** It is on by
default for every test in the repository.

If you genuinely want one test to call the real API — to check your parsing
against reality once, by hand — mark it:

    @pytest.mark.network
    def test_the_real_api_still_returns_what_i_expect():
        ...

It is deselected by default (see `pytest.ini`), so it cannot creep into the
build, and nothing in the push loop runs it.

**Keys.** A test marked `network` also gets the values in `.env` (only the
names not already set), so it can call an API that needs the app's key. No
other test does: they run exactly as they run in the build, where there is no
`.env`. A test of what your app does when a key is missing sets it up itself,
with `monkeypatch.delenv("NAME", raising=False)`.
"""

from __future__ import annotations

import importlib.util
import os
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


def _dot_env() -> dict:
    """The values in `.env`, read by `scripts/local_env.py`, or none."""
    path = ROOT / "scripts" / "local_env.py"
    if not path.is_file():
        return {}
    spec = importlib.util.spec_from_file_location("_pippa_local_env", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values: dict = {}
    module.load(ROOT / ".env", environ=values)
    return values


def _dot_env() -> dict:
    """The values in `.env`, read by `scripts/local_env.py`, or none."""
    path = ROOT / "scripts" / "local_env.py"
    if not path.is_file():
        return {}
    spec = importlib.util.spec_from_file_location("_pippa_local_env", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values: dict = {}
    module.load(ROOT / ".env", environ=values)
    return values


def _no_author_name_yet() -> bool:
    """True while manifest.yaml names nobody, as the template ships it.

    `app_author_name: ""` is the template's placeholder, and until it is
    filled in (Claude asks for it first, CLAUDE.md step 1) the Pippa SDK
    refuses the manifest, so `App()` cannot be built and every test of the app
    would fail with the same sentence. The build publishes nothing in that
    state ("Nothing to publish yet") and runs no tests, so the tests are
    skipped here too, with the reason, rather than failing for something that
    is not a bug.

    An older manifest with `publisher:` under `app:` instead still names
    somebody, so its tests run.
    """
    try:
        import yaml

        data = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict) or "app_author_name" not in data:
        return False
    named = data.get("app_author_name")
    publisher = data.get("app", {}).get("publisher") if isinstance(data.get("app"), dict) else None
    return all(value is None or (isinstance(value, str) and not value.strip())
               for value in (named, publisher))


def pytest_collection_modifyitems(config, items):
    """Skip the app's tests while manifest.yaml has no author name yet.

    Only the app's: the tests in `scripts/` cover the template's own tools,
    which need no author name.
    """
    if not _no_author_name_yet():
        return
    skip = pytest.mark.skip(
        reason="manifest.yaml has no app_author_name yet, so the Pippa SDK refuses "
               "it. Fill it in first (CLAUDE.md, step 1).",
    )
    scripts = ROOT / "scripts"
    for item in items:
        if scripts not in Path(item.path).resolve().parents:
            item.add_marker(skip)


class NetworkUsedInATest(RuntimeError):
    """A test tried to open a socket."""


_real_socket = socket.socket
_real_create_connection = socket.create_connection


def _refuse(where: str, address=None):
    target = ""
    if isinstance(address, (tuple, list)) and address:
        target = f" to {address[0]}"
    raise NetworkUsedInATest(
        f"a test tried to open a network connection{target} (via {where}).\n"
        "\n"
        "Tests must not call the real API: the suite would then fail offline, "
        "and its expected values would change whenever the data does.\n"
        "\n"
        "Replace the one method that does the HTTP, on the instance:\n"
        "\n"
        "    app = App()\n"
        "    app._fetch = lambda url, timeout=6.0: SAMPLE_RESPONSE"
    )


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """Refuse every outbound connection for the duration of each test.

    A test marked `network` is let through, with the keys from `.env`.
    """
    if request.node.get_closest_marker("network"):
        for name, value in _dot_env().items():
            if name not in os.environ:
                monkeypatch.setenv(name, value)
        yield
        return

    class _Blocked(_real_socket):
        def connect(self, address):          # noqa: D102 - stdlib signature
            _refuse("socket.connect", address)

        def connect_ex(self, address):       # noqa: D102
            _refuse("socket.connect_ex", address)

    def _blocked_create_connection(address, *args, **kwargs):
        _refuse("socket.create_connection", address)

    socket.socket = _Blocked
    socket.create_connection = _blocked_create_connection
    try:
        yield
    finally:
        socket.socket = _real_socket
        socket.create_connection = _real_create_connection
