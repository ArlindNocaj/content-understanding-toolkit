# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the explicit Azure CLI parameter inventory."""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest

from azext_content_understanding._params import load_arguments
from azext_content_understanding.commands import APPROVED_COMMAND_PATHS


class FakeContext:
    def __init__(self, arguments: dict[str, dict[str, Any]]) -> None:
        self.arguments = arguments

    def argument(self, name: str, **kwargs: Any) -> None:
        raise AssertionError(f"{name} must be registered with extra(), not argument()")

    def extra(self, name: str, **kwargs: Any) -> None:
        self.arguments[name] = kwargs


class FakeLoader:
    def __init__(self) -> None:
        self.arguments: dict[str, dict[str, dict[str, Any]]] = {}
        self.seen_commands: list[str] = []

    @contextmanager
    def argument_context(self, command: str) -> Iterator[FakeContext]:
        self.seen_commands.append(command)
        yield FakeContext(self.arguments.setdefault(command, {}))


@pytest.mark.unit
@pytest.mark.parametrize("path", APPROVED_COMMAND_PATHS)
def test_every_approved_command_loads_explicit_parameters(path: tuple[str, ...]) -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    for argument in loader.arguments["cu " + " ".join(path)].values():
        assert all(option.startswith("-") for option in argument.get("options_list", []))


@pytest.mark.unit
def test_analyze_uses_named_non_conflicting_options() -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    analyze = loader.arguments["cu analyze"]
    assert analyze["files"]["options_list"] == ["--file"]
    assert analyze["sources"]["options_list"] == ["--source"]
    assert analyze["urls"]["options_list"] == ["--url"]
    assert analyze["analyzer_id"]["options_list"] == ["--analyzer-name"]


@pytest.mark.unit
def test_loader_initialization_registers_the_complete_approved_surface() -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    assert set(loader.seen_commands) == {
        "cu " + " ".join(path) for path in APPROVED_COMMAND_PATHS
    }
