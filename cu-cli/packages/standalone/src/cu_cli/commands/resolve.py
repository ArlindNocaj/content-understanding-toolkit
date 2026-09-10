# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu resolve`` — turn rich-markdown ids into page, bounding box and context.

Purely local: reads a ``.result.json`` (full result) or ``.result.map.json``
written by ``cu analyze`` and never calls the service.
"""

from __future__ import annotations

import json
from pathlib import Path

import rich_click as click

from cu_cli_core.rich_markdown import RichMarkdownError, resolve_ids

from ..errors import CuCliError, friendly_errors
from ..exit_codes import VALIDATION_FAILURE
from ..output import dump_json


@click.command(
    "resolve",
    help="Resolve rich-markdown anchors (s3, t0, f2, p30) to page + bbox (+ context).",
    epilog="Ids come from `cu analyze FILE` (s3 = section, t0 = table, f2 = figure) or "
           "`cu analyze FILE --md-rich=paragraph` (p30 = paragraph). SOURCE is the "
           "matching --json result (text + context) or --map sidecar (page + bbox only). "
           "Coordinates are in inches on the page; bbox = {page, x, y, w, h}.\n\n"
           "[white] [/white]\n\n"
           "[bold cyan]Common commands:[/bold cyan]\n\n"
           "[bold green]cu resolve[/bold green] [bold yellow]doc.json p30[/bold yellow]\n\n"
           "[white]\u00a0\u00a0Page, bbox and text of paragraph 30.[/white]\n\n"
           "[bold green]cu resolve[/bold green] [bold yellow]doc.json p30[/bold yellow] "
           "[bold cyan]--around 2[/bold cyan]\n\n"
           "[white]\u00a0\u00a0Also the two paragraphs before and after it.[/white]\n\n"
           "[bold green]cu resolve[/bold green] [bold yellow]doc.json t0[/bold yellow] "
           "[bold cyan]--page --pages 1[/bold cyan]\n\n"
           "[white]\u00a0\u00a0Table 0 plus every element on its page and the neighbouring "
           "pages (with page size and page markdown).[/white]",
)
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("ids", nargs=-1, required=True, metavar="ID...")
@click.option("--around", type=click.IntRange(0, 50), default=0, metavar="N",
              help="Include N paragraphs before and after (markdown order).")
@click.option("--page", "page", is_flag=True,
              help="Include page geometry, page markdown and all elements on the page.")
@click.option("--pages", type=click.IntRange(0, 20), default=0, metavar="N",
              help="With --page: also include N pages before and after.")
@click.option("--text-chars", type=click.IntRange(0), default=400, metavar="N",
              help="Truncate returned text to N characters (0 = full text).")
@click.option("--raw", is_flag=True, help="Include the untouched element JSON.")
@friendly_errors
def cmd_resolve(source: Path, ids: tuple[str, ...], around: int, page: bool, pages: int,
                text_chars: int, raw: bool) -> None:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CuCliError(f"cannot read {source}: {exc}", exit_code=VALIDATION_FAILURE) from exc
    if not isinstance(payload, dict):
        raise CuCliError(
            f"{source} is not a cu analyze result or id map.",
            hint="pass the file written by `cu analyze FILE --json PATH` or `--map PATH`.",
            exit_code=VALIDATION_FAILURE,
        )
    try:
        resolved = resolve_ids(
            payload,
            ids,
            around=around,
            page=page,
            pages=pages,
            text_chars=None if text_chars == 0 else text_chars,
            raw=raw,
        )
    except RichMarkdownError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    resolved["source"] = str(source)
    dump_json(resolved)
