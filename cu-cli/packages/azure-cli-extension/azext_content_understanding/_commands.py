# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Thin command entry points for the Content Understanding extension."""

from __future__ import annotations

from typing import Any, Callable

from cu_cli_core.serialization import to_plain_value

from . import _analysis, _analyzers, _defaults, _diagnostics, _profiles
from ._errors import azure_cli_error


def _invoke(function: Callable[..., Any], cmd: Any, values: dict[str, Any]) -> Any:
    try:
        return to_plain_value(function(cmd, **values))
    except Exception as exc:  # Azure CLI owns final rendering and exit behavior.
        raise azure_cli_error(exc) from exc


def list_analyzers(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.list_analyzers, cmd, kwargs)


def show_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.show_analyzer, cmd, kwargs)


def create_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.create_analyzer, cmd, kwargs)


def delete_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.delete_analyzer, cmd, kwargs)


def validate_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.validate_analyzer, cmd, kwargs)


def create_analyzer_schema(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.create_analyzer_schema, cmd, kwargs)


def test_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.test_analyzer, cmd, kwargs)


def copy_analyzer(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.copy_analyzer, cmd, kwargs)


def analyze(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analysis.analyze, cmd, kwargs)


def show_defaults(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_defaults.show_defaults, cmd, kwargs)


def set_defaults(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_defaults.set_defaults, cmd, kwargs)


def show_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.show_profile, cmd, kwargs)


def list_profiles(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.list_profiles, cmd, kwargs)


def get_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.get_profile, cmd, kwargs)


def set_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.set_profile, cmd, kwargs)


def unset_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.unset_profile, cmd, kwargs)


def create_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.create_profile, cmd, kwargs)


def delete_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.delete_profile, cmd, kwargs)


def copy_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.copy_profile, cmd, kwargs)


def rename_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.rename_profile, cmd, kwargs)


def set_active_profile(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.set_active_profile, cmd, kwargs)


def sync_profile_defaults(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.sync_profile_defaults, cmd, kwargs)


def doctor(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_diagnostics.doctor, cmd, kwargs)


def list_environment_variables(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_diagnostics.list_environment_variables, cmd, kwargs)
