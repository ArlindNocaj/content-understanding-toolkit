# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Argument registration for the Content Understanding extension."""

from azure.cli.core.commands.parameters import get_enum_type

from cu_cli_core.command_spec import ANALYZER_LIST
from cu_cli_core.service_options import API_VERSION, ENDPOINT


def load_arguments(loader, command):
    if command != "cu analyzer list":
        return

    arguments = {argument.parser_name: argument for argument in ANALYZER_LIST.arguments}
    with loader.argument_context(command) as context:
        context.argument(
            ENDPOINT.parser_name,
            options_list=[ENDPOINT.name],
            help=ENDPOINT.help,
        )
        context.argument(
            API_VERSION.parser_name,
            options_list=[API_VERSION.name],
            help=API_VERSION.help,
        )
        context.argument(
            "profile_name",
            options_list=["--profile"],
            help="CU CLI profile used to resolve endpoint and API-version defaults.",
        )
        kind = arguments["kind"]
        context.argument(
            kind.parser_name,
            options_list=[kind.name],
            arg_type=get_enum_type(kind.choices),
            default=kind.default,
            help=kind.help,
        )
        sort_by = arguments["sort_by"]
        context.argument(
            sort_by.parser_name,
            options_list=[sort_by.name],
            arg_type=get_enum_type(sort_by.choices),
            default=sort_by.default,
            help=sort_by.help,
        )
