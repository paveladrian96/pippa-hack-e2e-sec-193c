"""Tests for scripts/local_env.py, which reads `.env` on your computer.

NOT a test of your app, and not a file you need to touch. Every value here is
an obvious fake.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import local_env  # noqa: E402


def test_the_usual_dot_env_forms_are_read():
    text = (
        "# Keys for running the app on this computer\n"
        "\n"
        "PLAIN=test-key-000000000000000000\n"
        'DOUBLE="has spaces # and a hash"\n'
        "SINGLE='single quoted'\n"
        "export EXPORTED=from-a-shell-script\n"
        "COMMENTED=value   # a comment after it\n"
        "EMPTY=\n"
        "  SPACED  =  around  \n"
        "not a line at all\n"
        "1BAD=starts with a digit\n"
    )
    assert local_env.parse(text) == {
        "PLAIN": "test-key-000000000000000000",
        "DOUBLE": "has spaces # and a hash",
        "SINGLE": "single quoted",
        "EXPORTED": "from-a-shell-script",
        "COMMENTED": "value",
        "EMPTY": "",
        "SPACED": "around",
    }


def test_a_name_already_set_is_left_alone_and_only_names_are_returned(tmp_path):
    path = tmp_path / ".env"
    path.write_text("WEATHER_API_KEY=test-key-000000000000000000\nALREADY=from-file\n",
                    encoding="utf-8")
    environ = {"ALREADY": "from-the-terminal"}
    loaded = local_env.load(path, environ)
    assert loaded == ["WEATHER_API_KEY"]
    assert environ == {"ALREADY": "from-the-terminal",
                       "WEATHER_API_KEY": "test-key-000000000000000000"}


def test_a_file_saved_by_windows_notepad_is_read(tmp_path):
    path = tmp_path / ".env"
    path.write_bytes("﻿FIRST=one\r\nSECOND=two\r\n".encode("utf-8"))
    environ: dict = {}
    assert local_env.load(path, environ) == ["FIRST", "SECOND"]
    assert environ == {"FIRST": "one", "SECOND": "two"}


def test_no_dot_env_is_not_an_error(tmp_path):
    environ: dict = {}
    assert local_env.load(tmp_path / ".env", environ) == []
    assert environ == {}


def test_the_real_environment_is_the_default_and_restored_by_the_caller(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("PIPPA_TEMPLATE_TEST_ONLY_NAME=test-key-000000000000000000\n", encoding="utf-8")
    monkeypatch.delenv("PIPPA_TEMPLATE_TEST_ONLY_NAME", raising=False)
    import os

    assert local_env.load(path) == ["PIPPA_TEMPLATE_TEST_ONLY_NAME"]
    assert os.environ["PIPPA_TEMPLATE_TEST_ONLY_NAME"] == "test-key-000000000000000000"
    monkeypatch.delenv("PIPPA_TEMPLATE_TEST_ONLY_NAME")
