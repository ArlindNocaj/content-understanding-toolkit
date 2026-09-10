# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the additive output flags, default analyzer resolution and ``cu resolve``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from cu_cli.cli import main
from cu_cli.commands.analyze import _select_outputs
from cu_cli.errors import CuCliError
from cu_cli.modality import DEFAULT_ANALYZER_ENV, default_analyzer_for

pytestmark = pytest.mark.unit

MARKDOWN = "# Title\n\nFirst para.\n\n<table><tr><td>a</td></tr></table>\n\nLast para.\n"


def _service_result() -> dict:
    """A realistic (tiny) documentSearch-style result envelope."""
    table_html = "<table><tr><td>a</td></tr></table>"
    table_at = MARKDOWN.index("<table>")
    return {
        "id": "op-secret-123",
        "status": "Succeeded",
        "result": {
            "analyzerId": "prebuilt-documentSearch",
            "contents": [
                {
                    "kind": "document",
                    "unit": "inch",
                    "markdown": MARKDOWN,
                    "startPageNumber": 1,
                    "endPageNumber": 1,
                    "pages": [
                        {
                            "pageNumber": 1,
                            "width": 8.5,
                            "height": 11,
                            "spans": [{"offset": 0, "length": len(MARKDOWN)}],
                        }
                    ],
                    "paragraphs": [
                        {
                            "role": "title",
                            "content": "Title",
                            "span": {"offset": 0, "length": 7},
                            "source": "D(1,1,1,2,1,2,1.5,1,1.5)",
                        },
                        {
                            "content": "First para.",
                            "span": {"offset": MARKDOWN.index("First"), "length": 11},
                            "source": "D(1,1,2,3,2,3,2.5,1,2.5)",
                        },
                        {
                            "content": "Last para.",
                            "span": {"offset": MARKDOWN.index("Last"), "length": 10},
                            "source": "D(1,1,5,3,5,3,5.5,1,5.5)",
                        },
                    ],
                    "tables": [
                        {
                            "rowCount": 1,
                            "columnCount": 1,
                            "span": {"offset": table_at, "length": len(table_html)},
                            "source": "D(1,1,4,4,4,4,4.5,1,4.5)",
                        }
                    ],
                    "sections": [
                        {
                            "span": {"offset": 0, "length": len(MARKDOWN)},
                            "elements": ["/paragraphs/0", "/paragraphs/1", "/tables/0", "/paragraphs/2"],
                        }
                    ],
                }
            ],
        },
    }


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def analyze_runtime(monkeypatch):
    monkeypatch.delenv(DEFAULT_ANALYZER_ENV, raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, _service_result()),
    )


def _run(runner: CliRunner, *args: str):
    return runner.invoke(main, list(args))


# ------------------------------------------------------------- _select_outputs
def test_select_outputs_defaults_to_rich_markdown_on_stdout():
    outputs, level = _select_outputs(
        md_rich=None, md_output=None, json_output=None, map_output=None,
        level=None, llm_input=False, output_file=None, single=True,
    )
    assert outputs == {"rich": "-"}
    assert level == "coarse"


def test_select_outputs_level_shorthand_and_explicit_paths():
    outputs, level = _select_outputs(
        md_rich="paragraph", md_output="doc.md", json_output="doc.json", map_output=None,
        level=None, llm_input=False, output_file=None, single=True,
    )
    assert level == "paragraph"
    assert outputs == {"rich": "-", "full": "doc.json", "llm-input": "doc.md"}


def test_select_outputs_rejects_two_streams_to_stdout_for_one_file():
    with pytest.raises(CuCliError):
        _select_outputs(
            md_rich="-", md_output=None, json_output="-", map_output=None,
            level=None, llm_input=False, output_file=None, single=True,
        )


def test_select_outputs_multi_file_uses_default_sidecars():
    outputs, _ = _select_outputs(
        md_rich=None, md_output=None, json_output="-", map_output="-",
        level=None, llm_input=False, output_file=None, single=False,
    )
    assert outputs == {"full": None, "map": None}


def test_select_outputs_multi_file_rejects_explicit_path():
    with pytest.raises(CuCliError):
        _select_outputs(
            md_rich=None, md_output=None, json_output="one.json", map_output=None,
            level=None, llm_input=False, output_file=None, single=False,
        )


def test_select_outputs_output_file_binds_to_the_streaming_view():
    outputs, _ = _select_outputs(
        md_rich=None, md_output=None, json_output="-", map_output="m.json",
        level=None, llm_input=False, output_file=Path("out.json"), single=True,
    )
    assert outputs == {"full": "out.json", "map": "m.json"}


def test_select_outputs_conflicting_level_is_an_error():
    with pytest.raises(CuCliError):
        _select_outputs(
            md_rich="coarse", md_output=None, json_output=None, map_output=None,
            level="paragraph", llm_input=False, output_file=None, single=True,
        )


# ------------------------------------------------------- default analyzer
def test_default_analyzer_precedence(monkeypatch):
    monkeypatch.delenv(DEFAULT_ANALYZER_ENV, raising=False)
    assert default_analyzer_for("a.pdf") == "prebuilt-documentSearch"
    assert default_analyzer_for("a.png") == "prebuilt-imageSearch"
    assert default_analyzer_for("a.mp3") == "prebuilt-audioSearch"
    assert default_analyzer_for("a.mp4") == "prebuilt-videoSearch"
    assert default_analyzer_for("a.pdf", profile_default="prebuilt-layout") == "prebuilt-layout"
    monkeypatch.setenv(DEFAULT_ANALYZER_ENV, "my-analyzer")
    assert default_analyzer_for("a.pdf", profile_default="prebuilt-layout") == "my-analyzer"
    assert default_analyzer_for("a.pdf", explicit="prebuilt-invoice") == "prebuilt-invoice"


# ------------------------------------------------------- analyze end to end
def test_analyze_default_streams_rich_markdown_with_coarse_ids(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        res = _run(runner, "analyze", "doc.pdf")

        assert res.exit_code == 0, res.output
        assert "<!--s0-->" in res.output
        assert "<!--t0-->" in res.output
        assert "<!--p0-->" not in res.output
        assert "First para." in res.output


def test_analyze_writes_all_views_from_one_call(runner, analyze_runtime, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (calls.append(job.input_ref) or (job, _service_result())),
    )
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        res = _run(
            runner, "analyze", "doc.pdf", "--md-rich=paragraph",
            "--md", "doc.md", "--json", "doc.json", "--map", "doc.map.json",
        )

        assert res.exit_code == 0, res.output
        assert len(calls) == 1
        assert "<!--s0,p0-->" in res.output
        assert "<!--p2-->Last para." in res.output

        plain = Path("doc.md").read_text(encoding="utf-8")
        assert "<!--p" not in plain and "First para." in plain

        full = json.loads(Path("doc.json").read_text(encoding="utf-8"))
        assert "id" not in full  # operation id stripped by default
        assert full["result"]["contents"][0]["markdown"] == MARKDOWN

        id_map = json.loads(Path("doc.map.json").read_text(encoding="utf-8"))
        assert id_map["schema"] == "cu-cli/id-map/v1"
        assert id_map["level"] == "paragraph"
        assert id_map["ids"]["p2"]["bbox"]["page"] == 1


def test_analyze_deletes_service_result_unless_keep_result(runner, analyze_runtime, monkeypatch):
    seen: list[bool] = []
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (seen.append(job.delete_result) or (job, _service_result())),
    )
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        assert _run(runner, "analyze", "doc.pdf").exit_code == 0
        assert _run(runner, "analyze", "doc.pdf", "--keep-result").exit_code == 0
    assert seen == [True, False]


def test_analyze_with_operation_id_keeps_id(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        res = _run(runner, "analyze", "doc.pdf", "--json", "--with-operation-id")

        assert res.exit_code == 0, res.output
        assert json.loads(res.output)["id"] == "op-secret-123"


def test_analyze_directory_writes_rich_and_json_sidecars(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("docs").mkdir()
        Path("docs/a.pdf").write_bytes(b"%PDF-1.4 a")
        Path("docs/b.pdf").write_bytes(b"%PDF-1.4 b")
        res = _run(runner, "analyze", "docs", "--json", "--map", "-d", "out", "-y")

        assert res.exit_code == 0, res.output
        names = sorted(p.name for p in Path("out").iterdir())
        assert names == [
            "a.pdf.result.json", "a.pdf.result.map.json",
            "b.pdf.result.json", "b.pdf.result.map.json",
        ]


def test_analyze_dry_run_lists_outputs_and_analyzer(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        res = _run(runner, "analyze", "doc.pdf", "--dry-run", "--json", "doc.json")

        assert res.exit_code == 0, res.output
        assert "prebuilt-" in res.output
        assert "doc.json" in res.output


# ------------------------------------------------------------------ resolve
def test_resolve_from_full_result_and_from_map(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        assert _run(
            runner, "analyze", "doc.pdf", "--md-rich", "doc.rich.md",
            "--json", "doc.json", "--map", "doc.map.json",
        ).exit_code == 0

        res = _run(runner, "resolve", "doc.json", "p1", "--around", "1")
        assert res.exit_code == 0, res.output
        payload = json.loads(res.output)
        assert payload["schema"] == "cu-cli/resolve/v1"
        assert payload["source"].endswith("doc.json")
        (item,) = payload["results"]
        assert item["page"] == 1
        assert item["text"] == "First para."
        assert [p["id"] for p in item["before"]] == ["p0"]
        assert [p["id"] for p in item["after"]] == ["t0"]

        res = _run(runner, "resolve", "doc.map.json", "t0", "p1")
        assert res.exit_code == 0, res.output
        by_id = {r["id"]: r for r in json.loads(res.output)["results"]}
        assert by_id["t0"]["bbox"] == {"page": 1, "x": 1.0, "y": 4.0, "w": 3.0, "h": 0.5}
        assert by_id["p1"]["error"] == "unknown id"  # coarse map has no paragraphs


def test_resolve_page_view(runner, analyze_runtime):
    with runner.isolated_filesystem():
        Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
        assert _run(runner, "analyze", "doc.pdf", "--json", "doc.json").exit_code == 0

        res = _run(runner, "resolve", "doc.json", "t0", "--page", "--text-chars", "0")
        assert res.exit_code == 0, res.output
        (item,) = json.loads(res.output)["results"]
        (page,) = item["pages"]
        assert page["page"] == 1
        assert page["width"] == 8.5
        # Sections have no bbox (they may span pages) and are not page elements.
        assert {e["id"] for e in page["elements"]} == {"p0", "p1", "t0", "p2"}


def test_resolve_rejects_non_result_json(runner):
    with runner.isolated_filesystem():
        Path("x.json").write_text("[1, 2]", encoding="utf-8")
        res = _run(runner, "resolve", "x.json", "p0")
        assert res.exit_code != 0
        assert "not a cu analyze result" in res.output
