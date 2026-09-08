# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Command registration for the Content Understanding extension."""


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

    with loader.command_group("cu", is_preview=True) as group:
        group.custom_command("analyze", "analyze_file")

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
    return loader.command_table
