# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Argument registration for the Content Understanding extension."""

import logging

from azure.cli.core.commands.parameters import get_enum_type

from cu_cli_core.command_spec import (
    ANALYZE,
    ANALYZER_COPY,
    ANALYZER_CREATE,
    ANALYZER_DELETE,
    ANALYZER_LIST,
    ANALYZER_SCHEMA_CREATE,
    ANALYZER_SHOW,
    ANALYZER_TEST,
    ANALYZER_VALIDATE,
    DEFAULTS_SET,
    PROFILE_COPY,
    PROFILE_CREATE,
    PROFILE_DELETE,
    PROFILE_GET,
    PROFILE_RENAME,
    PROFILE_SET,
    PROFILE_SET_ACTIVE,
    PROFILE_SHOW,
    PROFILE_SYNC_DEFAULTS,
    PROFILE_UNSET,
)
from cu_cli_core.service_options import API_VERSION, ENDPOINT


logger = logging.getLogger(__name__)


class _ExplicitArgumentContext:
    """Add arguments that are intentionally absent from variadic command wrappers."""

    def __init__(self, context) -> None:
        self._context = context

    def argument(self, argument_dest, **kwargs) -> None:
        self._context.extra(argument_dest, **kwargs)


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


def _load_command_arguments(loader, command: str) -> None:
    with loader.argument_context(command) as raw_context:
        context = _ExplicitArgumentContext(raw_context)
        if command in {
            "cu analyze",
            "cu analyzer list",
            "cu analyzer show",
            "cu analyzer create",
            "cu analyzer delete",
            "cu analyzer test",
            "cu analyzer copy",
            "cu analyzer schema create",
            "cu defaults show",
            "cu defaults set",
            "cu doctor",
            "cu profile sync-defaults",
        }:
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
        elif command == "cu analyzer validate":
            schema = _argument(ANALYZER_VALIDATE, "named_schema_path")
            context.argument(
                schema.parser_name,
                options_list=[schema.name],
                required=True,
                help=schema.help,
            )
            for parser_name in ("strict", "use_spec"):
                argument = _argument(ANALYZER_VALIDATE, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    action="store_true",
                    help=argument.help,
                )
        elif command == "cu analyzer schema create":
            for parser_name in ("from_template", "force"):
                argument = _argument(ANALYZER_SCHEMA_CREATE, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    action="store_true",
                    help=argument.help,
                )
            for parser_name in ("sample_path", "analyzer_id", "base", "out_path"):
                argument = _argument(ANALYZER_SCHEMA_CREATE, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    default=argument.default,
                    help=argument.help,
                )
            for parser_name in ("modality", "template_type"):
                argument = _argument(ANALYZER_SCHEMA_CREATE, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    arg_type=get_enum_type(argument.choices),
                    default=argument.default,
                    help=argument.help,
                )
        elif command == "cu analyzer test":
            _named_analyzer_argument(context, ANALYZER_TEST)
            _input_arguments(context, ANALYZER_TEST, include_urls=False)
            for parser_name in ("dry_run", "force", "assume_yes"):
                argument = _argument(ANALYZER_TEST, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    action="store_true",
                    help=argument.help,
                )
            output = _argument(ANALYZER_TEST, "out_path")
            context.argument(output.parser_name, options_list=[output.name], help=output.help)
            concurrency = _argument(ANALYZER_TEST, "concurrency")
            context.argument(
                concurrency.parser_name,
                options_list=[concurrency.name],
                type=int,
                default=concurrency.default,
                help=concurrency.help,
            )
        elif command == "cu analyzer copy":
            for parser_name in (
                "named_source",
                "named_destination",
                "source_resource",
                "source_subscription",
                "source_resource_group",
                "source_profile",
                "destination_resource",
                "destination_subscription",
                "destination_resource_group",
                "destination_profile",
            ):
                argument = _argument(ANALYZER_COPY, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    required=argument.required,
                    help=argument.help,
                )
        elif command == "cu analyze":
            _input_arguments(context, ANALYZE, include_urls=True)
            analyzer = _argument(ANALYZE, "analyzer_id")
            context.argument(
                analyzer.parser_name,
                options_list=["--analyzer-name"],
                help=analyzer.help,
            )
            for parser_name in ("inline", "show_usage", "llm_input", "dry_run", "assume_yes"):
                argument = _argument(ANALYZE, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    action="store_true",
                    help=argument.help,
                )
            for parser_name in ("output_file", "out_dir", "report_path"):
                argument = _argument(ANALYZE, parser_name)
                context.argument(parser_name, options_list=[argument.name], help=argument.help)
            existing = _argument(ANALYZE, "on_existing")
            context.argument(
                existing.parser_name,
                options_list=[existing.name],
                arg_type=get_enum_type(existing.choices),
                help=existing.help,
            )
            concurrency = _argument(ANALYZE, "concurrency")
            context.argument(
                concurrency.parser_name,
                options_list=[concurrency.name],
                type=int,
                default=concurrency.default,
                help=concurrency.help,
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
        elif command == "cu profile show":
            _optional_profile_name(context, PROFILE_SHOW)
        elif command in {"cu profile get", "cu profile unset"}:
            spec = PROFILE_GET if command.endswith(" get") else PROFILE_UNSET
            key = _argument(spec, "profile_key")
            context.argument(key.parser_name, options_list=[key.name], required=True, help=key.help)
            _optional_profile_name(context, spec)
        elif command == "cu profile set":
            for parser_name in ("profile_key", "profile_value"):
                argument = _argument(PROFILE_SET, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    required=True,
                    help=argument.help,
                )
            _optional_profile_name(context, PROFILE_SET)
        elif command in {"cu profile create", "cu profile delete", "cu profile set-active"}:
            spec = {
                "cu profile create": PROFILE_CREATE,
                "cu profile delete": PROFILE_DELETE,
                "cu profile set-active": PROFILE_SET_ACTIVE,
            }[command]
            name = _argument(spec, "profile_name")
            context.argument(name.parser_name, options_list=[name.name], required=True, help=name.help)
            if command == "cu profile delete":
                context.argument("yes", options_list=["--yes"], action="store_true", help="Skip confirmation.")
        elif command in {"cu profile copy", "cu profile rename"}:
            spec = PROFILE_COPY if command.endswith(" copy") else PROFILE_RENAME
            for parser_name in ("source_profile", "destination_profile"):
                argument = _argument(spec, parser_name)
                context.argument(
                    parser_name,
                    options_list=[argument.name],
                    required=argument.required,
                    help=argument.help,
                )
        elif command == "cu profile sync-defaults":
            _optional_profile_name(context, PROFILE_SYNC_DEFAULTS)
        elif command == "cu infra generate":
            context.argument(
                "output_dir",
                options_list=["--output-dir", "-d"],
                default="provision",
                help="Directory where the azd/Bicep project is generated.",
            )
            context.argument(
                "environment",
                options_list=["--environment", "-e"],
                help="azd environment name; prompted on a TTY and otherwise defaults to 'dev'.",
            )
            context.argument(
                "location",
                options_list=["--location", "-l"],
                help="Content Understanding Azure region.",
            )
            context.argument(
                "api_version",
                options_list=["--api-version"],
                help="Content Understanding service API version written to the azd environment.",
            )
            context.argument(
                "models",
                options_list=["--models"],
                help="'recommended', 'none', or comma-separated model or model@version selectors.",
            )
            context.argument(
                "foundry_endpoint",
                options_list=["--foundry-endpoint"],
                help="Existing Microsoft Foundry endpoint; mutually exclusive with --foundry-prefix.",
            )
            context.argument(
                "foundry_prefix",
                options_list=["--foundry-prefix"],
                help="Prefix for a new Microsoft Foundry resource.",
            )
            context.argument(
                "assign_roles",
                options_list=["--assign-roles"],
                action="store_true",
                default=None,
                help="Configure RBAC role assignments in the generated project.",
            )
            context.argument(
                "no_assign_roles",
                options_list=["--no-assign-roles"],
                action="store_true",
                help="Skip generated RBAC role assignments; subsequent az cu commands require existing access.",
            )
            context.argument(
                "force",
                options_list=["--force"],
                action="store_true",
                help="Replace an existing generated project and azd environment state.",
            )
            context.argument(
                "yes",
                options_list=["--yes", "-y"],
                action="store_true",
                help="Use deterministic defaults without showing the interactive wizard.",
            )
        elif command == "cu _infra-models":
            for parser_name, option in (
                ("resource_group", "--resource-group"),
                ("account_name", "--account"),
                ("selection", "--selection"),
                ("out_path", "--out"),
                ("endpoint", "--endpoint"),
                ("api_version", "--api-version"),
            ):
                context.argument(
                    parser_name,
                    options_list=[option],
                    required=parser_name not in {"api_version"},
                    help=f"Internal infrastructure model setup value: {parser_name}.",
                )
            context.argument(
                "deploy",
                options_list=["--deploy"],
                action="store_true",
                default=True,
                help="Deploy selected models before writing the Bicep model file.",
            )
            context.argument(
                "use_key",
                options_list=["--use-key"],
                action="store_true",
                help="Use an account key for the Content Understanding data-plane request.",
            )


def _input_arguments(context, spec, *, include_urls: bool) -> None:
    for parser_name in ("files", "sources"):
        argument = _argument(spec, parser_name)
        context.argument(
            parser_name,
            options_list=[argument.name],
            action="append",
            help=argument.help,
        )
    if include_urls:
        argument = _argument(spec, "urls")
        context.argument(
            argument.parser_name,
            options_list=[argument.name],
            action="append",
            help=argument.help,
        )
    pattern = _argument(spec, "pattern")
    context.argument(pattern.parser_name, options_list=[pattern.name], help=pattern.help)
    recursive = _argument(spec, "recursive")
    context.argument(
        recursive.parser_name,
        options_list=[recursive.name],
        action="store_true",
        help=recursive.help,
    )


def _optional_profile_name(context, spec) -> None:
    name = _argument(spec, "profile_name")
    context.argument(name.parser_name, options_list=[name.name], help=name.help)


def load_arguments(loader, command) -> None:
    """Register arguments for the complete approved CLI surface."""

    from .commands import APPROVED_COMMAND_PATHS, INTERNAL_COMMAND_PATHS

    logger.debug(
        "Loading Content Understanding arguments for requested command %r "
        "(active command %r, command string %r)",
        command,
        getattr(loader, "command_name", None),
        getattr(
            getattr(getattr(loader, "cli_ctx", None), "invocation", None),
            "data",
            {},
        ).get("command_string"),
    )

    for path in APPROVED_COMMAND_PATHS:
        _load_command_arguments(loader, "cu " + " ".join(path))
    for path in INTERNAL_COMMAND_PATHS:
        _load_command_arguments(loader, "cu " + " ".join(path))
