# Azure Content Understanding extension for Azure CLI

This preview extension adds Azure Content Understanding commands under `az cu`.
It uses the identity, cloud, and active subscription selected by Azure CLI and
supports standard Azure CLI output formats and JMESPath queries.

> [!IMPORTANT]
> This package is an implementation preview. The `az cu` command name and public
> Azure CLI extension registration remain subject to Azure CLI maintainer review.

## Content Understanding concepts

Content Understanding processes documents, images, audio, and video into
structured output. An **analyzer** defines how a file is processed. A
**prebuilt analyzer** is supplied by the service, while a **custom analyzer**
uses a field schema defined for an application.

Further reading:

- [What is Content Understanding?](https://learn.microsoft.com/azure/ai-services/content-understanding/overview)
- [Content Understanding terminology](https://learn.microsoft.com/azure/ai-services/content-understanding/glossary)

## Install and connect

Install Azure CLI, sign in, and install the extension wheel produced by this
repository. After extension-index publication, installation by name will use
`az extension add --name content-understanding`.

```bash
# Sign in and select the Azure subscription used by az cu commands.
az login

# Install a locally built preview extension wheel.
az extension add --source ./content_understanding-0.1.0b1-py3-none-any.whl

# Save the Microsoft Foundry endpoint in the default CU profile.
az cu profile set \
	--key endpoint \
	--value https://<resource-name>.services.ai.azure.com/

# Verify endpoint connectivity, authentication, and model readiness.
az cu doctor --output table
```

## Use `az cu` and `cu` interchangeably

The Azure CLI extension and standalone CU CLI are two frontends over the same
`cu-cli-core` operations. Install either frontend, or install both and move
between them for the same analyzer, analysis, defaults, profile, diagnostics,
and infrastructure-generation workflows.

Both frontends read and write the same `[cu]` profile settings in the active
Azure CLI configuration file (`~/.azure/config` by default, or the file under
`AZURE_CONFIG_DIR`). An endpoint, API version, default analyzer, active profile,
or model-deployment mapping saved with one frontend is immediately available to
the other. For example:

```bash
# Save the endpoint with the Azure CLI extension.
az cu profile set \
	--key endpoint \
	--value https://<resource-name>.services.ai.azure.com/

# Use the same default profile with the standalone frontend.
cu analyzer list

# Change the default analyzer with the standalone frontend.
cu profile set default_analyzer prebuilt-layout

# Use that setting with the Azure CLI extension.
az cu analyze --file document.pdf
```

The command names and capabilities overlap, but frontend conventions differ:

| Azure CLI extension | Standalone CU CLI |
| --- | --- |
| Starts commands with `az cu`. | Starts commands with `cu` (`cu-cli` on macOS). |
| Uses explicit options plus global Azure CLI `--output`, `--query`, and `--subscription`. | Supports standalone positional shortcuts and Rich/JSON output options. |
| Always uses the active `az login` identity; shared API keys and `auth_mode` do not override Azure CLI host authentication. | Uses the profile's `auth_mode` and can use a saved API key. |

Run `az cu <command> --help` or `cu <command> --help` when translating a command
between frontends. Profile values are shared; authentication sessions are not,
so sign in with `az login` before using `az cu`.

## Use prebuilt analyzers

Download the public sample invoice so the following examples are runnable from
the current directory:

```bash
# Download the Azure Content Understanding sample invoice.
curl --fail --location --output invoice.pdf \
	https://raw.githubusercontent.com/Azure-Samples/azure-ai-content-understanding-assets/main/document/invoice.pdf
```

Inspect available analyzers and process the invoice:

```bash
# List all analyzers available on the configured resource.
az cu analyzer list --output table

# Show the prebuilt invoice analyzer definition.
az cu analyzer show --name prebuilt-invoice

# Analyze the downloaded invoice and return its complete structured result.
az cu analyze \
	--file invoice.pdf \
	--analyzer-name prebuilt-invoice
```

Use standard Azure CLI queries to select results. This example lists the
mortgage analyzer IDs documented under
[`prebuilt-schema/2025-11-01/mortgage.us`](../../../prebuilt-schema/2025-11-01/mortgage.us):

```bash
# Return only analyzer IDs whose names start with prebuilt-mortgage.
az cu analyzer list \
	--query "[?starts_with(analyzerId, 'prebuilt-mortgage')].analyzerId" \
	--output tsv
```

Analyze remote input without downloading it first:

```bash
# Analyze the public sample invoice directly from its HTTPS URL.
az cu analyze \
	--url https://raw.githubusercontent.com/Azure-Samples/azure-ai-content-understanding-assets/main/document/invoice.pdf \
	--analyzer-name prebuilt-invoice
```

Azure Blob SAS parameters are sent to the service but redacted from reports and
errors. Large batches require confirmation unless `--yes` is supplied.

## Create a custom analyzer

Custom analyzers require supported model deployments and Content Understanding
defaults. Inspect defaults, create a schema, create an analyzer, and test it:

```bash
# Show the resource's model-to-deployment defaults.
az cu defaults show --output table

# Derive a starter extraction schema from the sample invoice.
az cu analyzer schema create \
	--from-sample invoice.pdf \
	--output-file invoice-schema.json

# Create a custom analyzer after reviewing and editing the generated schema.
az cu analyzer create \
	--name invoice_v1 \
	--schema invoice-schema.json

# Run the custom analyzer over the sample and write a structured test report.
az cu analyzer test \
	--name invoice_v1 \
	--file invoice.pdf \
	--output-file test-report.json \
	--yes
```

## Generate Microsoft Foundry infrastructure

`az cu infra generate` writes a self-contained azd/Bicep project. It does not
provision resources or run `azd up`. On a terminal it offers subscription,
resource, region, model, and RBAC choices; use `--yes` for deterministic
automation.

```bash
# Generate the project interactively using Azure CLI subscription context.
az cu infra generate --output-dir provision

# Enter the generated project directory.
cd provision

# Authenticate Azure Developer CLI for infrastructure deployment.
azd auth login

# Provision the generated project and run its az cu post-provision setup.
azd up
```

Generated hooks use the internal `az cu _infra-models` helper and do not require
the standalone `cu-cli` package.

## Command overview

| Command | Purpose |
| --- | --- |
| `az cu analyze` | Analyze local files, directories, or HTTPS URLs. |
| `az cu analyzer` | List, show, create, copy, delete, validate, and test analyzers and schemas. |
| `az cu defaults` | Read or configure model-to-deployment defaults. |
| `az cu profile` | Manage local endpoint, API version, and model settings. |
| `az cu infra generate` | Generate an azd/Bicep project; the user runs `azd up`. |
| `az cu doctor` | Return structured connectivity and readiness checks. |
| `az cu env-var list` | Inspect recognized environment variables with secrets redacted. |

This extension intentionally does not register direct provisioning or
self-upgrade. Update an indexed installation with
`az extension update --name content-understanding`.

## Implementation boundary

The runtime depends on `cu-cli-core`, not the standalone `cu_cli` package, and
does not import Click or Rich. The wheel contains a build-time snapshot of the
repository's canonical azd/Bicep template. Microsoft Entra authentication uses
the active Azure CLI host credential. This preview supports AzureCloud only.

For standalone CLI documentation and detailed CU workflows, see the
[CU CLI README](../../README.md).
