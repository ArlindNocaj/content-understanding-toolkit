# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Rich markdown: stable element ids that resolve back to page + bounding box.

Content Understanding returns, next to the markdown, a structured view of the
document (``sections`` / ``paragraphs`` / ``tables`` / ``figures``). Every
element carries a ``span`` (``offset``/``length`` in **code points** of the
markdown string, ``result.stringEncoding == "codePoint"``) and a ``source``
(``D(page, x1,y1, ..., x4,y4)`` polygon in inches).

This module derives short, stable ids from that structure and injects them
into the markdown as HTML comments::

    <!--s3--> ## 3 Results          section 3  (coarse)
    <!--t0--> | col | col |          table 0    (coarse)
    <!--f2--> ![](figures/...)       figure 2   (coarse)
    <!--p30--> Lorem ipsum ...       paragraph 30 (``paragraph`` level)

The id numbering is the element's index in the corresponding result array, so
``p30`` is ``result.contents[0].paragraphs[30]`` — nothing has to be derived
from the markdown. Injection is one linear pass over the sorted offsets; the
``pages[].spans`` are shifted so downstream page markers stay aligned. The
marker syntax ``<!--p30-->`` costs 4 tokens in the o200k tokenizer; coarse ids
add roughly 1 % to a multi-page document.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Callable, Iterable, Mapping

LEVELS = ("coarse", "paragraph")
DEFAULT_LEVEL = "coarse"

# When several elements start at the same offset the outer one is listed first.
_KIND_ORDER = {"s": 0, "f": 1, "t": 2, "p": 3}
_ID_RE = re.compile(r"^([sftp])(\d+)$")
_SOURCE_RE = re.compile(r"^D\((\d+),(.*)\)$")
_MARKER_RE = re.compile(r"<!--([sftp]\d+(?:,[sftp]\d+)*)-->")

MAP_SCHEMA = "cu-cli/id-map/v1"
RESOLVE_SCHEMA = "cu-cli/resolve/v1"


class RichMarkdownError(ValueError):
    """Raised for malformed ids or results that cannot carry ids."""


# --------------------------------------------------------------------------- helpers
def parse_bbox(source: str | None) -> dict[str, Any] | None:
    """``D(page,x1,y1,...)`` -> ``{"page", "x", "y", "w", "h"}`` (axis-aligned box)."""
    match = _SOURCE_RE.match(source or "")
    if not match:
        return None
    values = [float(v) for v in match.group(2).split(",") if v.strip()]
    if len(values) < 4:
        return None
    xs, ys = values[0::2], values[1::2]
    return {
        "page": int(match.group(1)),
        "x": round(min(xs), 4),
        "y": round(min(ys), 4),
        "w": round(max(xs) - min(xs), 4),
        "h": round(max(ys) - min(ys), 4),
    }


def _sort_key(element_id: str) -> tuple[int, int]:
    match = _ID_RE.match(element_id)
    if not match:
        raise RichMarkdownError(f"invalid element id {element_id!r}")
    return _KIND_ORDER[match.group(1)], int(match.group(2))


def _pointer_to_id(pointer: str) -> str | None:
    """``/paragraphs/12`` -> ``p12``; unknown pointers return ``None``."""
    parts = pointer.strip("/").split("/")
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    prefix = {"sections": "s", "figures": "f", "tables": "t", "paragraphs": "p"}.get(parts[0])
    return None if prefix is None else f"{prefix}{parts[1]}"


def _content_of(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    contents = result.get("contents") or []
    for content in contents:
        if isinstance(content, Mapping) and isinstance(content.get("markdown"), str):
            return content
    return None


def unwrap_result(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept the operation envelope ``{"status", "result"}`` or a bare result."""
    if "result" in payload and isinstance(payload["result"], Mapping):
        return payload["result"]
    return payload


# --------------------------------------------------------------------------- id map
def build_id_map(content: Mapping[str, Any], level: str = DEFAULT_LEVEL) -> dict[str, Any]:
    """Return the compact ``id -> {kind, span, bbox, ...}`` sidecar for *content*.

    ``coarse`` covers sections, tables and figures; ``paragraph`` adds every
    paragraph (``p<i>``). The map is intentionally small: an agent reads it
    instead of the full result to turn an id into page + bbox.
    """
    if level not in LEVELS:
        raise RichMarkdownError(f"level must be one of {'|'.join(LEVELS)} (got {level!r}).")
    ids: dict[str, dict[str, Any]] = {}

    for index, section in enumerate(content.get("sections") or []):
        if "span" not in section:
            continue
        ids[f"s{index}"] = {
            "kind": "section",
            "span": dict(section["span"]),
            "children": list(section.get("elements") or []),
        }
    for index, figure in enumerate(content.get("figures") or []):
        if "span" not in figure:
            continue
        entry: dict[str, Any] = {
            "kind": figure.get("kind") or "figure",
            "span": dict(figure["span"]),
            "bbox": parse_bbox(figure.get("source")),
        }
        if figure.get("id") is not None:
            entry["cuId"] = figure["id"]
        caption = (figure.get("caption") or {}).get("content")
        if caption:
            entry["caption"] = caption
        entry["children"] = list(figure.get("elements") or [])
        ids[f"f{index}"] = entry
    for index, table in enumerate(content.get("tables") or []):
        if "span" not in table:
            continue
        entry = {
            "kind": "table",
            "span": dict(table["span"]),
            "bbox": parse_bbox(table.get("source")),
            "rows": table.get("rowCount"),
            "cols": table.get("columnCount"),
        }
        caption = (table.get("caption") or {}).get("content")
        if caption:
            entry["caption"] = caption
        ids[f"t{index}"] = entry
    if level == "paragraph":
        # Paragraphs inside a table or figure (cells, axis labels, captions) are
        # addressed through their container id; anchoring them too would litter
        # <td> cells and image alt text with hundreds of markers.
        containers = [
            (int(e["span"]["offset"]), int(e["span"]["offset"]) + int(e["span"]["length"]))
            for e in ids.values()
            if e["kind"] != "section"
        ]
        for index, paragraph in enumerate(content.get("paragraphs") or []):
            if "span" not in paragraph:
                continue
            start = int(paragraph["span"]["offset"])
            if any(lo <= start < hi for lo, hi in containers):
                continue
            entry = {
                "kind": "paragraph",
                "span": dict(paragraph["span"]),
                "bbox": parse_bbox(paragraph.get("source")),
            }
            if paragraph.get("role"):
                entry["role"] = paragraph["role"]
            ids[f"p{index}"] = entry

    # Children are kept only when they resolve to ids present in this map so the
    # coarse map does not carry hundreds of dangling paragraph pointers.
    for entry in ids.values():
        children = entry.pop("children", None)
        if not children:
            continue
        resolved = [cid for cid in (_pointer_to_id(p) for p in children) if cid in ids]
        if resolved:
            entry["children"] = resolved

    return {
        "schema": MAP_SCHEMA,
        "level": level,
        "stringEncoding": "codePoint",
        "unit": content.get("unit") or "inch",
        "pageCount": len(content.get("pages") or []),
        "ids": ids,
    }


# --------------------------------------------------------------------------- injection
def inject_ids(
    markdown: str, id_map: Mapping[str, Any]
) -> tuple[str, Callable[[int], int]]:
    """Insert ``<!--id-->`` markers at every element's ``span.offset``.

    Returns ``(rich_markdown, shift)`` where ``shift(offset)`` maps an offset in
    the original markdown to the same position in the rich markdown (markers
    inserted *at* ``offset`` are considered to come after it, so a page span
    starting at that offset keeps pointing at the page's first character).
    """
    at_offset: dict[int, list[str]] = {}
    for element_id, entry in id_map["ids"].items():
        offset = int(entry["span"]["offset"])
        if 0 <= offset <= len(markdown):
            at_offset.setdefault(offset, []).append(element_id)

    inserts: list[tuple[int, int]] = []
    parts: list[str] = []
    last = 0
    for offset in sorted(at_offset):
        marker = "<!--" + ",".join(sorted(at_offset[offset], key=_sort_key)) + "-->"
        parts.append(markdown[last:offset])
        parts.append(marker)
        last = offset
        inserts.append((offset, len(marker)))
    parts.append(markdown[last:])

    def shift(original: int) -> int:
        return original + sum(length for offset, length in inserts if offset < original)

    return "".join(parts), shift


def with_rich_markdown(result: Mapping[str, Any], level: str = DEFAULT_LEVEL) -> dict[str, Any]:
    """Return a deep copy of *result* whose markdown carries ``<!--id-->`` markers.

    ``pages[].spans`` are shifted so that page markers added later by the SDK's
    ``to_llm_input`` still land on the first character of each page.
    """
    result_copy = copy.deepcopy(dict(result))
    for content in result_copy.get("contents") or []:
        markdown = content.get("markdown")
        if not isinstance(markdown, str):
            continue
        rich, shift = inject_ids(markdown, build_id_map(content, level))
        content["markdown"] = rich
        for page in content.get("pages") or []:
            for span in page.get("spans") or []:
                span["offset"] = shift(int(span["offset"]))
    return result_copy


def strip_ids(markdown: str) -> str:
    """Remove every ``<!--id-->`` marker (inverse of :func:`inject_ids`)."""
    return _MARKER_RE.sub("", markdown)


def render_llm_markdown(result: Mapping[str, Any]) -> str:
    """Render *result* (plain dict) through the SDK ``to_llm_input`` helper."""
    from azure.ai.contentunderstanding import to_llm_input
    from azure.ai.contentunderstanding.models import AnalysisResult

    rendered = to_llm_input(AnalysisResult(dict(result)))
    if not isinstance(rendered, str) or not rendered.strip():
        raise RuntimeError("to_llm_input() returned empty markdown output.")
    return rendered


def render_rich_markdown(result: Mapping[str, Any], level: str = DEFAULT_LEVEL) -> str:
    """Rich markdown = ids injected first, then the usual LLM-input rendering."""
    return render_llm_markdown(with_rich_markdown(result, level))


# --------------------------------------------------------------------------- resolve
def _text(markdown: str, span: Mapping[str, Any], limit: int | None) -> str:
    start = int(span["offset"])
    length = int(span["length"])
    if limit is not None:
        length = min(length, limit)
    return markdown[start : start + length]


def _page_of(entry: Mapping[str, Any]) -> int | None:
    bbox = entry.get("bbox")
    return None if not bbox else int(bbox["page"])


def _element_view(
    element_id: str,
    entry: Mapping[str, Any],
    markdown: str | None,
    *,
    text_chars: int | None,
) -> dict[str, Any]:
    view: dict[str, Any] = {"id": element_id, "kind": entry["kind"]}
    for key in ("cuId", "role", "rows", "cols", "caption", "children"):
        if entry.get(key) is not None:
            view[key] = entry[key]
    page = _page_of(entry)
    if page is not None:
        view["page"] = page
    if entry.get("bbox") is not None:
        view["bbox"] = entry["bbox"]
    view["span"] = entry["span"]
    if markdown is not None:
        view["text"] = _text(markdown, entry["span"], text_chars)
    return view


def resolve_ids(
    source: Mapping[str, Any],
    ids: Iterable[str],
    *,
    around: int = 0,
    page: bool = False,
    pages: int = 0,
    text_chars: int | None = 400,
    raw: bool = False,
) -> dict[str, Any]:
    """Resolve *ids* against a full result or an id map.

    :param source: a full analyze result (envelope or bare), or a map produced by
        :func:`build_id_map`. Text/context need the full result.
    :param around: also return that many blocks (paragraphs, tables, figures) before and after (markdown order).
    :param page: include every element on the element's page plus page geometry.
    :param pages: with ``page``, include that many neighbouring pages as well.
    :param text_chars: truncate returned text to this many characters (``None`` = full).
    :param raw: include the untouched element JSON from the result.
    """
    markdown: str | None = None
    content: Mapping[str, Any] | None = None
    if source.get("schema") == MAP_SCHEMA and "ids" in source:
        id_map = dict(source)
        level = id_map.get("level", DEFAULT_LEVEL)
    else:
        result = unwrap_result(source)
        content = _content_of(result)
        if content is None:
            raise RichMarkdownError("the source has no markdown content to resolve against.")
        markdown = content["markdown"]
        id_map = build_id_map(content, "paragraph")
        level = "paragraph"
    entries: dict[str, Any] = id_map["ids"]

    # Neighbours are the surrounding blocks (paragraphs, tables, figures) in
    # markdown order, not array order. Sections are containers, not blocks.
    ordered_blocks = sorted(
        (eid for eid in entries if not eid.startswith("s")),
        key=lambda eid: int(entries[eid]["span"]["offset"]),
    )

    results: list[dict[str, Any]] = []
    for element_id in ids:
        element_id = element_id.strip().lstrip("#")
        entry = entries.get(element_id)
        if entry is None:
            hint = (
                "paragraph ids need a full result or a paragraph-level map"
                if element_id.startswith("p") and level != "paragraph"
                else "check the id in the rich markdown (<!--id--> markers)"
            )
            results.append({"id": element_id, "error": "unknown id", "hint": hint})
            continue
        view = _element_view(element_id, entry, markdown, text_chars=text_chars)
        if raw and content is not None:
            view["raw"] = _raw_element(content, element_id)

        if around and markdown is not None:
            before, after = _neighbours(element_id, entry, ordered_blocks, entries, around)
            view["before"] = [
                _element_view(pid, entries[pid], markdown, text_chars=text_chars) for pid in before
            ]
            view["after"] = [
                _element_view(pid, entries[pid], markdown, text_chars=text_chars) for pid in after
            ]

        page_number = _page_of(entry)
        if page and page_number is not None:
            last_page = int(id_map.get("pageCount") or 0) or page_number + pages
            wanted = range(max(1, page_number - pages), min(last_page, page_number + pages) + 1)
            view["pages"] = [
                _page_view(number, content, entries, markdown, text_chars=text_chars)
                for number in wanted
            ]
        results.append(view)

    return {
        "schema": RESOLVE_SCHEMA,
        "unit": id_map.get("unit", "inch"),
        "stringEncoding": id_map.get("stringEncoding", "codePoint"),
        "results": results,
    }


def _neighbours(
    element_id: str,
    entry: Mapping[str, Any],
    ordered_blocks: list[str],
    entries: Mapping[str, Any],
    around: int,
) -> tuple[list[str], list[str]]:
    """Block ids (paragraph, table, figure) before/after *element_id* in markdown order.

    For containers (section, table, figure) the neighbours are the blocks just
    outside the container's span, so table cells or figure labels never count
    as context.
    """
    start = int(entry["span"]["offset"])
    end = start + int(entry["span"]["length"])
    before = [bid for bid in ordered_blocks
              if int(entries[bid]["span"]["offset"]) < start]
    after = [bid for bid in ordered_blocks
             if bid != element_id and int(entries[bid]["span"]["offset"]) >= end]
    return before[-around:] if around else [], after[:around]


def _raw_element(content: Mapping[str, Any], element_id: str) -> Any:
    match = _ID_RE.match(element_id)
    assert match is not None
    array = {"s": "sections", "f": "figures", "t": "tables", "p": "paragraphs"}[match.group(1)]
    return json.loads(json.dumps((content.get(array) or [])[int(match.group(2))]))


def _page_view(
    number: int,
    content: Mapping[str, Any] | None,
    entries: Mapping[str, Any],
    markdown: str | None,
    *,
    text_chars: int | None,
) -> dict[str, Any]:
    view: dict[str, Any] = {"page": number}
    if content is not None:
        for page in content.get("pages") or []:
            if int(page.get("pageNumber", 0)) == number:
                for key in ("width", "height", "angle"):
                    if page.get(key) is not None:
                        view[key] = page[key]
                spans = page.get("spans") or []
                if spans and markdown is not None:
                    view["span"] = spans[0]
                    view["markdown"] = _text(markdown, spans[0], None)
                break
    on_page = [
        eid for eid, entry in entries.items() if _page_of(entry) == number
    ]
    on_page.sort(key=lambda eid: (int(entries[eid]["span"]["offset"]), _sort_key(eid)))
    view["elements"] = [
        _element_view(eid, entries[eid], markdown, text_chars=text_chars) for eid in on_page
    ]
    return view
