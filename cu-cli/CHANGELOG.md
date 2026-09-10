# Release History

## Unreleased

### Features Added

- `cu analyze` no longer requires a configured analyzer: it picks one by file type (`prebuilt-documentSearch` for documents, `prebuilt-imageSearch` / `-audioSearch` / `-videoSearch` otherwise). `CU_DEFAULT_ANALYZER` overrides it; precedence is `--analyzer` › env › profile › file type.
- Output flags are additive and each names its destination: `--md-rich [PATH|coarse|paragraph]` (default), `--md [PATH]`, `--json [PATH]`, `--map [PATH]`. All views are rendered locally from one service call.
- Rich Markdown: `<!--s3-->` / `<!--t0-->` / `<!--f0-->` anchors before sections, tables and figures (and `<!--p30-->` per paragraph with `--md-rich=paragraph`). Ids are the array indices of the service result; removing the anchors yields the plain Markdown.
- Added `cu resolve RESULT.json ID... [--around N] [--page] [--pages N]` to turn anchors into page, bounding box, text and neighbouring blocks without a service call.
- Analysis results are deleted on the service after retrieval (`--keep-result` opts out); the operation id is omitted from `--json` unless `--with-operation-id` is given.

### Breaking Changes

- `--llm-input` is now a hidden alias of `--md`; `--output-file` on `cu analyze` is replaced by the per-view `PATH` values. Batch results are written as `NAME.result.rich.md` by default (`.result.md` with `--md`).

## 0.1.0b1 (2026-09-04)

### Features Added

- Initial release of CU CLI for using Azure Content Understanding from the terminal.
- Added `cu infra generate` to generate an azd/Bicep project used to provision a new or existing Microsoft Foundry resource, optionally deploy supported models, and configure Content Understanding defaults.
- Added `cu profile` to manage named profiles, resource endpoints, authentication, API versions, and model mappings.
- Added `cu doctor` to diagnose authentication, resource connectivity, and model readiness.
- Added `cu env-var` to document supported environment variables and inspect currently configured values with sensitive values redacted.
- Added `cu analyze` to process documents, images, audio, and video individually or in concurrent batches using prebuilt or custom analyzers, with Markdown or service JSON output.
- Added `cu analyzer` to list, inspect, create, copy, test, and delete analyzers, and to generate and validate local analyzer schemas.
- Added `cu defaults` to view and configure model-to-deployment mappings.
- Added `cu upgrade` to check for and explicitly install newer CU CLI releases; upgrades are never automatic.
- Added support for the `2025-11-01` GA API and the `2026-06-01-preview` API.
