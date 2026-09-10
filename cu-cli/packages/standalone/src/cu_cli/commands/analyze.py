# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu analyze`` standalone adapter."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from azure.core.exceptions import HttpResponseError
from cu_cli_core.command_spec import (
    ANALYZE,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
import rich_click as click
from rich.markup import escape as _esc

from ..apiversion import API_VERSION_HELP, ensure_supported, supports_api_feature
from ..client import build_client
from ..profile import Profile
from cu_cli_core.analysis import (
    AnalyzeJob,
    AnalyzeOutcome,
    AnalyzeResponse,
    analyze_one_inline,
    analyze_one_inline_with_usage,
    analyze_one_with_usage,
)
from ..errors import CuCliError, _format_service_error, friendly_errors
from ..exit_codes import GENERIC_ERROR, VALIDATION_FAILURE
from ..modality import DEFAULT_ANALYZER_ENV, default_analyzer_for
from ..output import (
    EmptyMarkdownOutputError,
    console,
    dump_json,
    dump_text,
    dumps_json,
    render_id_map,
    render_markdown,
    render_rich_markdown,
    to_jsonable,
)
from ._options import CALLING_TIME_OPTION, calling_time
from ._command_spec import with_command_arguments

if TYPE_CHECKING:
    from cu_cli_core.contracts import ExecutionPlan, ExistingResultPolicy, InputPlan, ResultView

# Output views in "primary" order: the first requested one is the job's
# ``out_path`` (used by --output-file, reports and dry-run listings).
_VIEW_ORDER = ("rich", "full", "llm-input", "map")
_VIEW_FLAG = {"rich": "--md-rich", "llm-input": "--md", "full": "--json", "map": "--map"}
_LEVELS = ("coarse", "paragraph")


def _warn_result_kept(job: AnalyzeJob, response: AnalyzeResponse) -> None:
    if job.delete_result and response.result_deleted is False:
        console.print(
            f"[yellow]warning:[/yellow] could not delete the service-side result for "
            f"{_esc(job.input_ref)}; it stays retrievable by operation id until retention expires."
        )


def _run_one(client, job: AnalyzeJob):
    """Thin, patchable seam around :func:`cu_cli_core.analysis.analyze_one_with_usage`.

    Kept as a module-level indirection so tests can inject a fake analyzer and
    so callers that want the originating job alongside the result get the
    familiar ``(job, result)`` tuple. All real work lives in ``core``.
    """
    response = analyze_one_with_usage(client, job)
    _warn_result_kept(job, response)
    return job, response.result


def _run_one_inline(client, job: AnalyzeJob):
    """Run one job through the synchronous inline analyze API."""
    return job, analyze_one_inline(client, job)


def _run_one_with_usage(client, job: AnalyzeJob):
    """Run one long-running analysis while retaining usage metadata."""
    response = analyze_one_with_usage(client, job)
    _warn_result_kept(job, response)
    return job, response


def _run_one_inline_with_usage(client, job: AnalyzeJob):
    """Run one inline analysis while retaining usage metadata."""
    return job, analyze_one_inline_with_usage(client, job)


def _print_usage(usage, *, input_ref: str) -> None:
    """Render request usage to stderr without changing data written to stdout."""
    console.print("\n")
    console.print(f"[bold cyan]Usage:[/bold cyan] {_esc(input_ref)}")
    if usage is None:
        console.print("[dim]usage details were not returned by the service.[/dim]")
        return
    console.print_json(data=to_jsonable(usage))


_ON_EXISTS_ENV = "CU_ON_EXISTS"
_ON_EXISTS_CHOICES = ("error", "skip", "reanalyze")


def _friendly_analyze_error(exc: BaseException) -> str:
    """Return a user-facing error string for per-input analyze failures."""
    msg = str(exc)
    if isinstance(exc, EmptyMarkdownOutputError) or (
        "to_llm_input() returned empty markdown output" in msg
    ):
        return (
            "Analysis succeeded, but the Markdown view was empty. "
            "Retry with --json to inspect the complete result."
        )
    if isinstance(exc, HttpResponseError):
        return _format_service_error(exc)
    return msg


def _resolve_on_exists(explicit: str | None) -> ExistingResultPolicy:
    """Resolve the explicit or environment-selected existing-result policy."""
    from cu_cli_core.contracts import ExistingResultPolicy

    raw = explicit or os.environ.get(_ON_EXISTS_ENV, "").strip().lower() or "error"
    if not raw:
        raw = "error"
    if raw not in _ON_EXISTS_CHOICES:
        raise CuCliError(
            f"{_ON_EXISTS_ENV} must be one of {'|'.join(_ON_EXISTS_CHOICES)} "
            f"(got {os.environ.get(_ON_EXISTS_ENV)!r}).",
            exit_code=VALIDATION_FAILURE,
        )
    return ExistingResultPolicy(raw)


def _validate_report_path(report_path: Path | None, jobs: list[AnalyzeJob]) -> None:
    """Reject a report path that would overwrite a finalized analysis result."""
    if report_path is None:
        return
    resolved_report_path = report_path.resolve(strict=False)
    for job in jobs:
        for planned in _job_files(job):
            if planned.resolve(strict=False) == resolved_report_path:
                raise CuCliError(
                    f"--report-file conflicts with an analysis result file: {report_path}",
                    hint=(
                        "choose a different --report-file path; planned result path: "
                        f"{planned}."
                    ),
                    exit_code=VALIDATION_FAILURE,
                )


def _job_files(job: AnalyzeJob) -> list[Path]:
    """Every file this job will write (all views), primary first."""
    files: list[Path] = []
    if job.out_path is not None:
        files.append(job.out_path)
    for path in job.outputs.values():
        if path is not None and path not in files:
            files.append(path)
    return files


def _preflight_output_writes(
    jobs: list[AnalyzeJob],
    *,
    report_path: Path | None,
) -> None:
    output_paths = [path for job in jobs for path in _job_files(job)]
    if report_path is not None:
        output_paths.append(report_path)

    directories = {path.parent.resolve(strict=False) for path in output_paths}
    for directory in sorted(directories, key=str):
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=directory,
            prefix=".cu-write-check-",
        ) as handle:
            handle.write(b"\0")
            handle.flush()


def _write_analyze_report(
    path: Path, *, analyzer_id, fmt: str, results: list[dict], outputs: list[str] | None = None
) -> None:
    """Write a machine-readable per-input status report (regression).

    ``results`` is a flat list of ``{"input", "status", ...}`` records where
    ``status`` is ``succeeded`` / ``failed`` / ``skipped``. The stable ``schema`` key
    lets agents parse the summary without scraping human-formatted stderr.
    """
    counts = {"succeeded": 0, "failed": 0, "skipped": 0}
    for r in results:
        status = r.get("status")
        if status in counts:
            counts[status] += 1
    counts["total"] = len(results)
    payload = dumps_json(
        {
            "schema": "cu-cli/analyze-report/v1",
            "analyzer": analyzer_id,
            "result_view": "full" if fmt == "json" else "llm-input",
            "outputs": outputs or (["full"] if fmt == "json" else ["rich"]),
            "counts": counts,
            "results": results,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _print_extension_counts(input_plan: InputPlan) -> None:
    for extension, count in input_plan.extension_counts.items():
        console.print(f"  {extension:<10} {count}")


def _print_discovery_skips(input_plan: InputPlan) -> None:
    if not input_plan.skipped:
        return
    console.print(f"Skipped during discovery: {len(input_plan.skipped)}")
    for item in input_plan.skipped:
        console.print(f"  [dim]- {_esc(str(item.path))}: {_esc(item.reason)}[/dim]")


def _print_discovery(input_plan: InputPlan, *, analyzer_id: str) -> None:
    console.print(f"[yellow]Found {len(input_plan.inputs)} files:[/yellow]")
    _print_extension_counts(input_plan)
    _print_discovery_skips(input_plan)
    console.print(f"\nAnalyzer: {analyzer_id}")
    console.print(f"Recursive: {'yes' if input_plan.recursive else 'no'}")


def _print_dry_run(
    plans: dict[str, ExecutionPlan], *, analyzer_id: str, level: str
) -> None:
    plan = next(iter(plans.values()))
    input_plan = plan.input_plan
    console.print("[bold cyan]Dry run[/bold cyan]")
    console.print(
        f"Selected: {len(input_plan.inputs)} file(s), {input_plan.total_bytes} byte(s)"
    )
    _print_extension_counts(input_plan)
    _print_discovery_skips(input_plan)
    console.print(f"Analyzer: {analyzer_id}")
    console.print(f"Outputs: {', '.join(_VIEW_FLAG[v] for v in plans)} (ids: {level})")
    console.print(f"Recursive: {'yes' if input_plan.recursive else 'no'}")
    console.print(f"On existing: {plan.on_existing.value}")
    for view, view_plan in plans.items():
        for output in view_plan.outputs:
            if output.path is None:
                destination = "stdout"
            else:
                destination = str(output.path)
            label = f"[dim]{_VIEW_FLAG[view]}[/dim] " if len(plans) > 1 else ""
            if output.exists:
                action = (
                    "skip"
                    if plan.on_existing.value == "skip"
                    else plan.on_existing.value
                )
                console.print(
                    f"  {label}{_esc(str(output.source.path))} -> {_esc(destination)} "
                    f"[dim](exists: {action})[/dim]"
                )
            else:
                console.print(f"  {label}{_esc(str(output.source.path))} -> {_esc(destination)}")
    console.print(
        "[dim]No service calls or files were written. Analyzer existence, "
        "service-side format acceptance, usage, and cost were not validated.[/dim]"
    )


def _looks_like_input(value: str) -> bool:
    """Guard against ``cu analyze --json doc.pdf`` swallowing the input as a path."""
    from ..modality import KNOWN_SERVICE_INPUT_EXTS

    path = Path(value)
    return path.suffix.lower() in KNOWN_SERVICE_INPUT_EXTS and path.is_file()


def _select_outputs(
    *,
    md_rich: str | None,
    md_output: str | None,
    json_output: str | None,
    map_output: str | None,
    level: str | None,
    llm_input: bool,
    output_file: Path | None,
    single: bool,
) -> tuple[dict[str, str | None], str]:
    """Turn the additive output flags into ``{view: destination}`` plus the id level.

    Destination ``"-"`` means stdout, a string is an explicit path, ``None`` means
    the default location (next to the input or under ``--output-dir``). With no
    flags the default is rich markdown to stdout (one file) or ``.result.rich.md``
    files (several files).
    """
    if md_rich in _LEVELS:
        if level is not None and level != md_rich:
            raise CuCliError(
                f"--md-rich={md_rich} conflicts with --level {level}.",
                exit_code=VALIDATION_FAILURE,
            )
        level, md_rich = md_rich, "-"
    level = level or _LEVELS[0]

    if llm_input:
        console.print("[yellow]--llm-input is deprecated; use --md instead.[/yellow]")
        md_output = md_output or "-"

    requested: dict[str, str | None] = {}
    for view, value in (
        ("rich", md_rich), ("full", json_output), ("llm-input", md_output), ("map", map_output)
    ):
        if value is None:
            continue
        requested[view] = value
    if not requested:
        requested["rich"] = "-"

    if output_file is not None:
        streaming = [v for v, d in requested.items() if d == "-"]
        if len(streaming) == 1:
            requested[streaming[0]] = str(output_file)
        elif len(requested) == 1:
            requested[next(iter(requested))] = str(output_file)
        else:
            raise CuCliError(
                "--output-file is ambiguous when several outputs are requested.",
                hint="give each output its own path, e.g. --md-rich a.md --json a.json.",
                exit_code=VALIDATION_FAILURE,
            )

    if single:
        streaming = [v for v, d in requested.items() if d == "-"]
        if len(streaming) > 1:
            raise CuCliError(
                "only one output can stream to stdout: "
                + " and ".join(_VIEW_FLAG[v] for v in streaming),
                hint="give a PATH to all but one, e.g. `--md-rich --json doc.json`.",
                exit_code=VALIDATION_FAILURE,
            )
    else:
        explicit = [v for v, d in requested.items() if d not in (None, "-")]
        if explicit:
            raise CuCliError(
                f"{_VIEW_FLAG[explicit[0]]} PATH is valid only when exactly one file is selected.",
                hint="drop the PATH to write .result.* files next to each input, "
                     "or add --output-dir DIR.",
                exit_code=VALIDATION_FAILURE,
            )
        requested = {view: None for view in requested}
    ordered = {view: requested[view] for view in _VIEW_ORDER if view in requested}
    return ordered, level


def _view_enum(view: str) -> ResultView:
    from cu_cli_core.contracts import ResultView

    return ResultView(view)


def _strip_operation_id(envelope: object) -> object:
    """Never echo the operation id: anyone with endpoint access can GET the result by it."""
    if isinstance(envelope, dict) and "id" in envelope and "result" in envelope:
        return {k: v for k, v in envelope.items() if k != "id"}
    return envelope


def _emit_outputs(
    job: AnalyzeJob,
    result,
    *,
    level: str,
    with_operation_id: bool,
) -> list[Path]:
    """Render every requested view of one result; return the files written."""
    written: list[Path] = []
    payload = result if isinstance(result, dict) else to_jsonable(result)
    for view, destination in job.outputs.items():
        if view == "rich":
            dump_text(render_rich_markdown(payload, level), destination)
        elif view == "llm-input":
            dump_text(render_markdown(payload), destination)
        elif view == "full":
            dump_json(payload if with_operation_id else _strip_operation_id(payload), destination)
        elif view == "map":
            dump_json(render_id_map(payload, level), destination)
        if destination is not None:
            written.append(destination)
    return written


def _describe_analyzer(explicit: str | None, profile_default: str | None) -> str:
    if explicit:
        return explicit
    env_default = os.environ.get(DEFAULT_ANALYZER_ENV, "").strip()
    if env_default:
        return f"{env_default} ({DEFAULT_ANALYZER_ENV})"
    if profile_default:
        return f"{profile_default} (profile default_analyzer)"
    return "auto (prebuilt-*Search by file type)"


@click.command("analyze",
               help=ANALYZE.help,
               epilog="Default output is markdown with element anchors (<!--s3--> section, <!--t0--> "
                      "table, <!--f2--> figure). Add [bold cyan]--md-rich=paragraph[/bold cyan] for paragraph ids, "
                      "then [bold green]cu resolve[/bold green] RESULT.json ID to get page + bbox. "
                      "Outputs are additive and all come from ONE service call.\n\n"
                      "When a result file already exists, analyze stops unless "
                      "--on-existing skip or --on-existing reanalyze is selected. "
                      "Set CU_ON_EXISTS=error|skip|reanalyze to change the default.\n\n"
                      "[white] [/white]\n\n"
                      "[bold cyan]Common commands:[/bold cyan]\n\n"
                      "[bold green]cu analyze[/bold green] [bold yellow]FILE[/bold yellow]\n\n"
                      "[white]\u00a0\u00a0Rich markdown to stdout (prebuilt-documentSearch for "
                      "documents, *Search prebuilts by file type).[/white]\n\n"
                      "[bold green]cu analyze[/bold green] [bold yellow]FILE[/bold yellow] "
                      "[bold cyan]--md-rich[/bold cyan] [bold yellow]doc.md[/bold yellow] "
                      "[bold cyan]--json[/bold cyan] [bold yellow]doc.json[/bold yellow]\n\n"
                      "[white]\u00a0\u00a0Markdown for the agent plus the full result for "
                      "id lookups, one call.[/white]\n\n"
                      "[bold green]cu analyze[/bold green] [bold yellow]FILE[/bold yellow] "
                      "[bold cyan]-a[/bold cyan] [bold magenta]prebuilt-invoice[/bold magenta] "
                      "[bold cyan]--json[/bold cyan]\n\n"
                      "[white]\u00a0\u00a0Extract invoice fields as JSON.[/white]\n\n"
                      "[bold green]cu analyze[/bold green] "
                      "[bold cyan]--source[/bold cyan] [bold yellow]DIRECTORY[/bold yellow] "
                      "[bold cyan]--output-dir[/bold cyan] [bold yellow]TARGET_DIR[/bold yellow]\n\n"
                      "[white]\u00a0\u00a0Analyze immediate files in DIRECTORY and write all "
                      "result files to TARGET_DIR instead of beside each input.[/white]")
@with_command_arguments(ANALYZE)
@CALLING_TIME_OPTION
@click.option("--llm-input", "llm_input", is_flag=True, hidden=True,
              help="Deprecated alias for --md.")
@click.option("-p", "--profile", "profile_name", default=None,
              help="Named CU CLI profile to use (from cu profile).")
@click.option("--endpoint", default=None, help="Override configured endpoint.")
@click.option("--auth-mode", type=click.Choice(["login", "key"]), default=None,
              help="Authentication mode; defaults to the selected CU CLI profile.")
@click.option("--api-key", default=None, help="Override configured API key.")
@click.option("--api-version", "api_version", default=None,
              help=API_VERSION_HELP)
@friendly_errors
def cmd_analyze(
    inputs,
    files,
    sources,
    pattern,
    recursive,
    analyzer_id,
    out_dir,
    output_file,
    llm_input,
    md_rich,
    md_output,
    json_output,
    map_output,
    level,
    with_operation_id,
    keep_result,
    report_path,
    concurrency,
    on_existing,
    dry_run,
    assume_yes,
    endpoint,
    api_key,
    api_version,
    auth_mode,
    profile_name,
    inline,
    show_usage,
    show_calling_time,
) -> None:
    from cu_cli_core.contracts import ExistingResultPolicy, InputOrigin
    from cu_cli_core.input_planning import plan_inputs, plan_outputs

    # `cu analyze --json doc.pdf` would bind doc.pdf as the --json path; catch it
    # before input validation so the user sees the actionable hint.
    for view, value in (
        ("rich", md_rich), ("llm-input", md_output), ("full", json_output), ("map", map_output)
    ):
        if value and value != "-" and value not in _LEVELS and _looks_like_input(value):
            raise CuCliError(
                f"{_VIEW_FLAG[view]} {value}: this looks like an input file, not an output path.",
                hint=f"put the input before the flag (`cu analyze FILE {_VIEW_FLAG[view]}`) or "
                     f"write `{_VIEW_FLAG[view]}=PATH`.",
                exit_code=VALIDATION_FAILURE,
            )

    try:
        request = build_request(
            ANALYZE,
            {
                "inputs": inputs,
                "files": files,
                "sources": sources,
                "pattern": pattern,
                "recursive": recursive,
                "analyzer_id": analyzer_id,
                "inline": inline,
                "show_usage": show_usage,
                "output_file": output_file,
                "out_dir": out_dir,
                "on_existing": on_existing,
                "dry_run": dry_run,
                "assume_yes": assume_yes,
                "report_path": report_path,
                "concurrency": concurrency,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc

    # Fail fast, before any input discovery, CU service call, or result-file
    # write: an existing report is never overwritten.
    if dry_run and assume_yes:
        raise CuCliError(
            "--dry-run and --yes cannot be combined.",
            exit_code=VALIDATION_FAILURE,
        )
    if not dry_run and report_path is not None and report_path.exists():
        raise CuCliError(
            f"--report-file already exists: {report_path}",
            hint="choose a new --report-file path; existing reports are never overwritten.",
            exit_code=VALIDATION_FAILURE,
        )
    input_plan = plan_inputs(
        positional=request.positional_inputs,
        files=request.files,
        sources=request.sources,
        pattern=request.pattern,
        recursive=request.recursive,
    )
    single = len(input_plan.inputs) == 1
    outputs, level = _select_outputs(
        md_rich=md_rich,
        md_output=md_output,
        json_output=json_output,
        map_output=map_output,
        level=level,
        llm_input=llm_input,
        output_file=request.output_file,
        single=single,
    )
    views = list(outputs)
    primary = views[0]
    fmt = "json" if primary == "full" else "markdown"
    skipped_report: list[dict] = []
    policy = _resolve_on_exists(request.on_existing)
    plans = {
        view: plan_outputs(
            input_plan,
            view=_view_enum(view),
            output_file=None if destination in (None, "-") else destination,
            output_dir=request.output_dir,
            on_existing=policy,
            stream_single=destination == "-",
            dry_run=dry_run,
        )
        for view, destination in outputs.items()
    }
    profile = Profile.load(profile_name=profile_name)
    analyzer_label = _describe_analyzer(request.analyzer, profile.default_analyzer)
    skipped_report = [
        {
            "input": str(item.path),
            "status": "skipped",
            "reason": item.reason,
            "output": None,
        }
        for item in input_plan.skipped
    ]

    jobs = []
    for index, item in enumerate(input_plan.inputs):
        job_outputs = {view: plans[view].outputs[index].path for view in views}
        jobs.append(
            AnalyzeJob(
                input_ref=str(item.path),
                analyzer_id=default_analyzer_for(
                    item.path,
                    explicit=request.analyzer,
                    profile_default=profile.default_analyzer,
                ),
                out_path=job_outputs[primary],
                # Every view is derived locally from the complete service result.
                output_format="json",
                outputs=job_outputs,
                # Inline analysis stores nothing on the service; LRO results do.
                delete_result=not keep_result and not inline,
            )
        )
    to_stdout = single and any(path is None for path in jobs[0].outputs.values())
    writes_files = any(_job_files(job) for job in jobs)

    effective_api_version = ensure_supported(api_version or profile.api_version)
    if inline:
        if not supports_api_feature(effective_api_version, "inline-analysis"):
            raise CuCliError(
                "--inline requires API version 2026-06-01-preview.",
                hint="pass `--api-version 2026-06-01-preview` or save it with "
                     "`cu profile set api_version 2026-06-01-preview`.",
            )

    skipped: list[Path] = []
    if dry_run:
        _print_dry_run(plans, analyzer_id=analyzer_label, level=level)
        return
    if writes_files:
        _validate_report_path(report_path, jobs)
        existing = [j for j in jobs if any(p.exists() for p in _job_files(j))]
        if existing:
            where = f"under {out_dir}" if out_dir is not None else "next to the inputs"
            if policy is ExistingResultPolicy.ERROR:
                raise CuCliError(
                    f"{len(existing)} of {len(jobs)} result file(s) already exist {where}.",
                    hint="choose --on-existing skip to keep them or "
                         "--on-existing reanalyze to replace them (re-bills).",
                    exit_code=VALIDATION_FAILURE,
                )
            if policy is ExistingResultPolicy.SKIP:
                skipped = [j.out_path for j in existing if j.out_path is not None]
                for j in existing:
                    skipped_report.append({
                        "input": j.input_ref,
                        "status": "skipped",
                        "reason": "result file already exists",
                        "output": str(j.out_path) if j.out_path is not None else None,
                    })
                existing_ids = {id(j) for j in existing}
                jobs = [j for j in jobs if id(j) not in existing_ids]
            elif policy is ExistingResultPolicy.REANALYZE:
                console.print(
                    "[yellow]Warning:[/yellow] Reanalysis sends the input to "
                    "Content Understanding again and may incur additional charges. "
                    "Existing result files will be replaced."
                )
        if not jobs:
            message = (
                f"[green]nothing to do:[/green] {len(skipped)} result file(s) already exist "
                "(skipped)."
            )
            if input_plan.skipped:
                message += f" {len(input_plan.skipped)} source entry(s) skipped during discovery."
            console.print(message)
            if report_path is not None:
                _write_analyze_report(report_path, analyzer_id=analyzer_label, fmt=fmt,
                                      results=skipped_report, outputs=views)
                console.print(f"[dim]report:[/dim] wrote {report_path}")
            return
        discovered = any(
            item.origin in {InputOrigin.POSITIONAL_SOURCE, InputOrigin.NAMED_SOURCE}
            for item in input_plan.inputs
        )
        if not assume_yes and discovered and len(jobs) > 1 and sys.stdin.isatty():
            _print_discovery(input_plan, analyzer_id=analyzer_label)
            if not click.confirm("proceed?", default=False):
                raise CuCliError("aborted by user.", hint="narrow the inputs or pass --yes.")

    _preflight_output_writes(jobs, report_path=report_path)
    client = build_client(profile, endpoint_override=endpoint, api_key_override=api_key,
                          api_version_override=api_version,
                          auth_mode_override=auth_mode)
    if show_usage:
        run_one = _run_one_inline_with_usage if inline else _run_one_with_usage
    else:
        run_one = _run_one_inline if inline else _run_one

    if to_stdout:
        job = jobs[0]
        with calling_time(show_calling_time) as calling_timer:
            batch_result = resolve_identifier(ANALYZE.operation)(
                client,
                request,
                input_plan=input_plan,
                jobs=[job],
                run=lambda c, j: run_one(c, j)[1],
            )
        if batch_result.failures:
            failure = batch_result.failures[0].error
            assert failure is not None
            # Match the batch path: a failed single-input run still emits the
            # --report file (one "failed" entry) before the friendly error exits
            # 1, so a scripted single-file caller never gets a missing report
            # (regression). Re-raise the captured core outcome so @friendly_errors
            # renders the same message and exit code as before.
            if report_path is not None:
                _write_analyze_report(
                    report_path, analyzer_id=analyzer_label, fmt=fmt, outputs=views,
                    results=[{"input": job.input_ref, "status": "failed",
                              "analyzer": job.analyzer_id,
                              "error": _friendly_analyze_error(failure)}] + skipped_report,
                )
                console.print(f"[dim]report:[/dim] wrote {report_path}")
            raise failure
        response = batch_result.successes[0].result
        if show_usage:
            assert isinstance(response, AnalyzeResponse)
            result = response.result
        else:
            result = response
        try:
            written = _emit_outputs(job, result, level=level, with_operation_id=with_operation_id)
        except RuntimeError as exc:  # EmptyMarkdownOutputError or the core renderer's RuntimeError
            if "empty markdown" not in str(exc):
                raise
            error = _friendly_analyze_error(exc)
            if report_path is not None:
                _write_analyze_report(
                    report_path,
                    analyzer_id=analyzer_label,
                    fmt=fmt,
                    outputs=views,
                    results=[
                        {
                            "input": job.input_ref,
                            "status": "failed",
                            "analyzer": job.analyzer_id,
                            "error": error,
                        }
                    ] + skipped_report,
                )
                console.print(f"[dim]report:[/dim] wrote {report_path}")
            raise CuCliError(error) from exc
        for path in written:
            console.print(f"  [green]->[/green] {path}")
        if report_path is not None:
            _write_analyze_report(
                report_path, analyzer_id=analyzer_label, fmt=fmt, outputs=views,
                results=[{"input": job.input_ref, "status": "succeeded",
                          "analyzer": job.analyzer_id,
                          "output": str(job.out_path) if job.out_path else None,
                          "files": [str(p) for p in written]}] + skipped_report,
            )
            console.print(f"[dim]report:[/dim] wrote {report_path}")
        if show_usage:
            assert isinstance(response, AnalyzeResponse)
            _print_usage(response.usage, input_ref=job.input_ref)
        calling_timer.print()
        return

    failures: list[tuple[str, str]] = []
    single_files: list[Path] = []
    results_report: list[dict] = []
    usage_results: list[tuple[str, object]] = []
    console.print(f"[bold]analyze[/bold] {len(jobs)} file(s) -> "
                  f"{out_dir or 'alongside inputs'} [dim]({', '.join(_VIEW_FLAG[v] for v in views)})[/dim]")

    def _persist(outcome: AnalyzeOutcome) -> None:
        job = outcome.job
        if not outcome.ok:
            assert outcome.error is not None
            err = _friendly_analyze_error(outcome.error)
            failures.append((job.input_ref, err))
            results_report.append({"input": job.input_ref, "status": "failed",
                                   "analyzer": job.analyzer_id, "error": err})
            return
        try:
            assert job.out_path is not None
            if show_usage:
                assert isinstance(outcome.result, AnalyzeResponse)
                result = outcome.result.result
                usage_results.append((job.input_ref, outcome.result.usage))
            else:
                result = outcome.result
            files = _emit_outputs(job, result, level=level, with_operation_id=with_operation_id)
            single_files.extend(files)
            results_report.append({"input": job.input_ref, "status": "succeeded",
                                   "analyzer": job.analyzer_id, "output": str(job.out_path),
                                   "files": [str(p) for p in files]})
        except Exception as exc:  # noqa: BLE001 — per-file isolation on write
            err = _friendly_analyze_error(exc)
            failures.append((job.input_ref, err))
            results_report.append({"input": job.input_ref, "status": "failed",
                                   "analyzer": job.analyzer_id, "error": err})

    with calling_time(show_calling_time) as calling_timer:
        resolve_identifier(ANALYZE.operation)(
            client,
            request,
            input_plan=input_plan,
            jobs=jobs,
            on_result=_persist,
            run=lambda c, j: run_one(c, j)[1],
        )

    # Write the report before the failure exit so agents always get it (regression).
    if report_path is not None:
        _write_analyze_report(report_path, analyzer_id=analyzer_label, fmt=fmt, outputs=views,
                              results=results_report + skipped_report)
        console.print(f"[dim]report:[/dim] wrote {report_path}")
    summary = [f"[green]{len(single_files)} ok[/green]", f"[red]{len(failures)} failed[/red]"]
    if skipped:
        summary.append(f"[dim]{len(skipped)} skipped (existing)[/dim]")
    if input_plan.skipped:
        summary.append(f"[dim]{len(input_plan.skipped)} skipped (discovery)[/dim]")
    console.print(", ".join(summary))
    for path in single_files:
        console.print(f"  [green]->[/green] {path}")
    if failures:
        # List every failed input and its full reason — never truncate the file
        # list or the per-file service message, so an agent can act on each one
        # (regression).
        console.print(f"[red]{len(failures)} failed input(s):[/red]")
        for ref, err in failures:
            console.print(f"  [red]x[/red] {_esc(ref)}")
            for line in (err.splitlines() or [""]):
                console.print(f"      [dim]{_esc(line)}[/dim]")
    for input_ref, usage in usage_results:
        _print_usage(usage, input_ref=input_ref)
    calling_timer.print()
    if failures:
        sys.exit(GENERIC_ERROR)
