# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Offline tests for the native Azure CLI command registration."""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
import yaml

from azext_content_understanding import _help  # noqa: F401
from azext_content_understanding.commands import (
    APPROVED_COMMAND_PATHS,
    SHARED_COMMAND_PATHS,
    load_command_table,
)


class FakeGroup:
    def __init__(self, path: str, registered: dict[str, dict[str, Any]]) -> None:
        self.path = path
        self.registered = registered

    def custom_command(self, name: str, operation: str, **kwargs: Any) -> None:
        self.registered[f"{self.path} {name}"] = {"operation": operation, **kwargs}


class FakeLoader:
    def __init__(self) -> None:
        self.command_table: dict[str, dict[str, Any]] = {}

    @contextmanager
    def command_group(self, path: str, **kwargs: Any) -> Iterator[FakeGroup]:
        assert kwargs["is_preview"] is True
        yield FakeGroup(path, self.command_table)


@pytest.mark.unit
def test_approved_preview_commands_are_registered_from_explicit_allowlist() -> None:
    loader = FakeLoader()

    command_table = load_command_table(loader, [])

    assert set(command_table) == {"cu " + " ".join(path) for path in APPROVED_COMMAND_PATHS}
    assert set(APPROVED_COMMAND_PATHS) - {("doctor",)} <= SHARED_COMMAND_PATHS
    assert command_table["cu analyzer list"]["table_transformer"].endswith(
        "#analyzer_list_table"
    )
    assert command_table["cu defaults show"]["table_transformer"].endswith("#defaults_table")


@pytest.mark.unit
def test_deferred_and_not_planned_commands_are_not_registered() -> None:
    loader = FakeLoader()

    command_table = load_command_table(loader, [])

    assert "cu infra generate" not in command_table
    assert "cu provision" not in command_table
    assert "cu _infra-models" not in command_table
    assert "cu _has-values" not in command_table
    assert "cu upgrade" not in command_table


@pytest.mark.unit
def test_all_help_entries_are_valid_yaml() -> None:
    from knack.help_files import helps

    for command_name in ("cu", *("cu " + " ".join(path) for path in APPROVED_COMMAND_PATHS)):
        parsed = yaml.safe_load(helps[command_name])
        assert isinstance(parsed, dict), command_name
        assert parsed["type"] in {"group", "command"}, command_name
