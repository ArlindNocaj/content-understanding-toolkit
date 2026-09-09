# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Command registration for the Content Understanding extension."""

from cu_cli_core.command_spec import COMMAND_SPECS


APPROVED_COMMAND_PATHS: tuple[tuple[str, ...], ...] = (
    ("analyze",),
    ("analyzer", "list"),
    ("analyzer", "show"),
    ("analyzer", "create"),
    ("analyzer", "delete"),
    ("analyzer", "validate"),
    ("analyzer", "schema", "create"),
    ("analyzer", "test"),
    ("analyzer", "copy"),
    ("defaults", "show"),
    ("defaults", "set"),
    ("profile", "show"),
    ("profile", "list"),
    ("profile", "get"),
    ("profile", "set"),
    ("profile", "unset"),
    ("profile", "create"),
    ("profile", "delete"),
    ("profile", "copy"),
    ("profile", "rename"),
    ("profile", "set-active"),
    ("profile", "sync-defaults"),
    ("doctor",),
    ("env-var", "list"),
    ("infra", "generate"),
)

INTERNAL_COMMAND_PATHS: tuple[tuple[str, ...], ...] = (("_infra-models",),)

# COMMAND_SPECS is used for drift checks only. Registration remains explicit so
# adding a shared command never makes it public in the extension by accident.
SHARED_COMMAND_PATHS = frozenset(spec.path for spec in COMMAND_SPECS)


def load_command_table(loader, _):
    with loader.command_group("cu analyzer", is_preview=True) as group:
        group.custom_command("show", "show_analyzer")
        group.custom_command(
            "list",
            "list_analyzers",
            table_transformer="azext_content_understanding._format#analyzer_list_table",
        )
        group.custom_command("create", "create_analyzer")
        group.custom_command("delete", "delete_analyzer")
        group.custom_command("validate", "validate_analyzer")
        group.custom_command("test", "test_analyzer")
        group.custom_command("copy", "copy_analyzer")

    with loader.command_group("cu analyzer schema", is_preview=True) as group:
        group.custom_command("create", "create_analyzer_schema")

    with loader.command_group("cu", is_preview=True) as group:
        group.custom_command("analyze", "analyze")
        group.custom_command("doctor", "doctor")

    with loader.command_group("cu defaults", is_preview=True) as group:
        group.custom_command(
            "show",
            "show_defaults",
            table_transformer="azext_content_understanding._format#defaults_table",
        )
        group.custom_command(
            "set",
            "set_defaults",
            table_transformer="azext_content_understanding._format#defaults_table",
        )

    with loader.command_group("cu profile", is_preview=True) as group:
        group.custom_command("show", "show_profile")
        group.custom_command(
            "list",
            "list_profiles",
            table_transformer="azext_content_understanding._format#profile_list_table",
        )
        group.custom_command("get", "get_profile")
        group.custom_command("set", "set_profile")
        group.custom_command("unset", "unset_profile")
        group.custom_command("create", "create_profile")
        group.custom_command("delete", "delete_profile")
        group.custom_command("copy", "copy_profile")
        group.custom_command("rename", "rename_profile")
        group.custom_command("set-active", "set_active_profile")
        group.custom_command("sync-defaults", "sync_profile_defaults")

    with loader.command_group("cu env-var", is_preview=True) as group:
        group.custom_command(
            "list",
            "list_environment_variables",
            table_transformer="azext_content_understanding._format#environment_table",
        )

    with loader.command_group("cu infra", is_preview=True) as group:
        group.custom_command("generate", "generate_infrastructure")

    with loader.command_group("cu", is_preview=True) as group:
        group.custom_command("_infra-models", "setup_infrastructure_models")
    return loader.command_table
