# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Command registration for the Content Understanding extension."""


def load_command_table(loader, _):
    with loader.command_group("cu analyzer", is_preview=True) as group:
        group.custom_command(
            "list",
            "list_analyzers",
            table_transformer="azext_content_understanding._format#analyzer_list_table",
        )
    return loader.command_table
