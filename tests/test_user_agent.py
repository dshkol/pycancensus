"""Tests for the user agent sent with CensusMapper API requests."""

import platform
import re
from unittest.mock import MagicMock

import pytest
import requests

import pycancensus as pc
from pycancensus import settings
from pycancensus.resilience import ResilientSession

ENV_VAR = settings.USER_AGENT_PREFIX_ENV_VAR


@pytest.fixture(autouse=True)
def clean_prefix(monkeypatch):
    """Isolate each test from prefixes set in code or the environment."""
    monkeypatch.setattr(settings, "_USER_AGENT_PREFIX", None)
    monkeypatch.delenv(ENV_VAR, raising=False)


def make_session():
    """A ResilientSession whose underlying requests session is mocked."""
    session = ResilientSession()
    session._min_request_interval = 0
    response = MagicMock(spec=requests.Response)
    response.status_code = 200
    response.ok = True
    session.session = MagicMock()
    session.session.request.return_value = response
    return session


def sent_headers(session):
    return session.session.request.call_args.kwargs["headers"]


def test_user_agent_identifies_package_and_versions():
    assert pc.get_user_agent() == (
        f"pycancensus/{pc.__version__} requests/{requests.__version__} "
        f"Python/{platform.python_version()}"
    )


def test_user_agent_is_a_valid_product_token_list():
    tokens = pc.get_user_agent().split(" ")
    assert [t.split("/")[0] for t in tokens] == ["pycancensus", "requests", "Python"]
    assert all(re.fullmatch(r"[\w.-]+/[\w.+-]+", t) for t in tokens)


def test_prefix_is_prepended_and_can_be_removed():
    pc.set_user_agent_prefix("mypackage/1.2.3")
    assert pc.get_user_agent().startswith("mypackage/1.2.3 pycancensus/")

    pc.set_user_agent_prefix(None)
    assert pc.get_user_agent().startswith("pycancensus/")

    pc.set_user_agent_prefix("")
    assert pc.get_user_agent().startswith("pycancensus/")


def test_prefix_control_characters_are_collapsed():
    pc.set_user_agent_prefix("  my\npackage/1.0\r\n\t ")
    assert pc.get_user_agent().startswith("my package/1.0 pycancensus/")


def test_whitespace_only_prefix_is_ignored():
    pc.set_user_agent_prefix(" \n ")
    assert pc.get_user_agent().startswith("pycancensus/")


def test_prefix_must_be_a_string():
    with pytest.raises(TypeError):
        pc.set_user_agent_prefix(123)


def test_env_var_sets_prefix(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "envtool/2.0")
    assert pc.get_user_agent().startswith("envtool/2.0 pycancensus/")


def test_prefix_set_in_code_overrides_env_var(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "envtool/2.0")
    pc.set_user_agent_prefix("codetool/3.0")
    ua = pc.get_user_agent()
    assert ua.startswith("codetool/3.0 pycancensus/")
    assert "envtool" not in ua


@pytest.mark.parametrize("method", ["get", "post"])
def test_requests_carry_the_user_agent(method):
    session = make_session()
    getattr(session, method)("https://censusmapper.ca/api/v1/list_datasets")
    assert sent_headers(session)["User-Agent"] == pc.get_user_agent()


def test_prefix_set_after_session_creation_applies():
    session = make_session()
    pc.set_user_agent_prefix("latecomer/0.1")
    session.get("https://censusmapper.ca/api/v1/list_datasets")
    assert sent_headers(session)["User-Agent"].startswith("latecomer/0.1 ")


def test_caller_headers_are_kept_and_can_override():
    session = make_session()
    session.get("https://example.test", headers={"Accept": "text/csv"})
    headers = sent_headers(session)
    assert headers["Accept"] == "text/csv"
    assert headers["User-Agent"] == pc.get_user_agent()

    session.get("https://example.test", headers={"User-Agent": "custom/1"})
    assert sent_headers(session)["User-Agent"] == "custom/1"
