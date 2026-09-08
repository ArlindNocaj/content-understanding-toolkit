# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Offline tests for the native Azure CLI command registration."""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest

from azext_content_understanding.commands import load_command_table


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
def test_initial_preview_commands_are_registered_without_frontend_imports() -> None:
    loader = FakeLoader()

    command_table = load_command_table(loader, [])

    assert set(command_table) == {
        "cu analyze",
        "cu analyzer create",
        "cu analyzer delete",
        "cu analyzer list",
        "cu analyzer show",
        "cu defaults set",
        "cu defaults show",
    }
    assert command_table["cu analyzer list"]["table_transformer"].endswith(
        "#analyzer_list_table"
    )
    assert command_table["cu defaults show"]["table_transformer"].endswith("#defaults_table")
