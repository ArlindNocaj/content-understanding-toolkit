# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Argument registration for the Content Understanding extension."""

from azure.cli.core.commands.parameters import get_enum_type

from cu_cli_core.command_spec import (
    ANALYZE,
    ANALYZER_CREATE,
    ANALYZER_DELETE,
    ANALYZER_LIST,
    ANALYZER_SHOW,
    DEFAULTS_SET,
)
from cu_cli_core.service_options import API_VERSION, ENDPOINT


def _service_arguments(context) -> None:
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


def _argument(spec, parser_name: str):
    return next(argument for argument in spec.arguments if argument.parser_name == parser_name)


def _named_analyzer_argument(context, spec) -> None:
    argument = _argument(spec, "analyzer_name")
    context.argument(
        argument.parser_name,
        options_list=[argument.name, "-n"],
        required=True,
        help=argument.help,
    )


def load_arguments(loader, command):
    with loader.argument_context(command) as context:
        _service_arguments(context)

        if command == "cu analyzer list":
            kind = _argument(ANALYZER_LIST, "kind")
            context.argument(
                kind.parser_name,
                options_list=[kind.name],
                arg_type=get_enum_type(kind.choices),
                default=kind.default,
                help=kind.help,
            )
            sort_by = _argument(ANALYZER_LIST, "sort_by")
            context.argument(
                sort_by.parser_name,
                options_list=[sort_by.name],
                arg_type=get_enum_type(sort_by.choices),
                default=sort_by.default,
                help=sort_by.help,
            )
        elif command == "cu analyzer show":
            _named_analyzer_argument(context, ANALYZER_SHOW)
        elif command == "cu analyzer create":
            _named_analyzer_argument(context, ANALYZER_CREATE)
            schema = _argument(ANALYZER_CREATE, "schema_path")
            context.argument(
                schema.parser_name,
                options_list=[schema.name, "-s"],
                required=True,
                help=schema.help,
            )
        elif command == "cu analyzer delete":
            _named_analyzer_argument(context, ANALYZER_DELETE)
            yes = _argument(ANALYZER_DELETE, "yes")
            context.argument(
                yes.parser_name,
                options_list=[yes.name, "-y"],
                action="store_true",
                help=yes.help,
            )
        elif command == "cu analyze":
            file_argument = _argument(ANALYZE, "files")
            context.argument(
                "file_path",
                options_list=[file_argument.name],
                required=True,
                help="Local file to analyze.",
            )
            analyzer = _argument(ANALYZE, "analyzer_id")
            context.argument(
                analyzer.parser_name,
                options_list=["--analyzer-name", "-a"],
                help=analyzer.help,
            )
        elif command == "cu defaults set":
            model = _argument(DEFAULTS_SET, "model_kv")
            context.argument(
                model.parser_name,
                options_list=[model.name],
                action="append",
                required=True,
                help=model.help,
            )
            replace = _argument(DEFAULTS_SET, "replace")
            context.argument(
                replace.parser_name,
                options_list=[replace.name],
                action="store_true",
                help=replace.help,
            )
