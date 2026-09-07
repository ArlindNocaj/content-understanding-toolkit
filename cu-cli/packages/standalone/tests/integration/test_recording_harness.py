# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the record/playback harness in :mod:`support.recording`."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from support.recording import _before_record_request, _before_record_response

pytestmark = pytest.mark.unit


def test_before_record_request_scrubs_sas_url_in_json_body() -> None:
    request = SimpleNamespace(
        uri="https://realacct.services.ai.azure.com/contentunderstanding/analyze",
        headers={},
        body=(
            '{"inputs":[{"url":"https://storage.example.test/c/input.pdf'
            '?sv=2026-01-01&sp=r&sig=top-secret"}]}'
        ),
    )

    out = _before_record_request(request)

    assert "top-secret" not in out.body
    assert "sig=REDACTED" in out.body
    assert "sv=REDACTED" in out.body


def test_before_record_response_scrubs_host_and_sensitive_query(monkeypatch) -> None:
    monkeypatch.setenv("CU_TEST_REC_ENDPOINT", "https://realacct.services.ai.azure.com/")
    response = {
        "headers": {},
        "body": {
            "string": (
                '{"containerUrl":"https://realacct.blob.core.windows.net/c?sv=2023-01-03&sig=abc123&sp=r"}'
            )
        },
    }

    out = _before_record_response(response)
    body = out["body"]["string"]
    assert "realacct.services.ai.azure.com" not in body
    assert "sig=REDACTED" in body
    assert "sv=REDACTED" in body


def test_before_record_response_handles_bytes_payload(monkeypatch) -> None:
    monkeypatch.setenv("CU_TEST_REC_ENDPOINT", "https://realacct.services.ai.azure.com/")
    response = {
        "headers": {},
        "body": {
            "string": b"https://realacct.services.ai.azure.com/path?code=abc"
        },
    }

    out = _before_record_response(response)
    body = out["body"]["string"]
    assert isinstance(body, bytes)
    assert b"sanitized.services.ai.azure.com" in body
    assert b"code=REDACTED" in body
