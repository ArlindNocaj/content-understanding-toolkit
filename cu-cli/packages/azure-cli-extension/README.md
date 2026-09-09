# Azure Content Understanding extension for Azure CLI

This preview extension adds Azure Content Understanding commands under `az cu`.

The preview supports analyzer management, local/URL/batch analysis, defaults,
profiles, diagnostics, and analyzer copy with the identity, cloud, and active
subscription selected by Azure CLI:

```bash
az login
az cu analyzer list --endpoint https://<resource-name>.services.ai.azure.com/
az cu analyzer show --name prebuilt-invoice
az cu analyze --file invoice.pdf --analyzer-name prebuilt-invoice
az cu analyze --url "https://storage.example/container/invoice.pdf?<sas>" --analyzer-name prebuilt-invoice
az cu analyze --source documents --recursive --output-dir results --yes
az cu defaults show --output table
az cu infra generate --output-dir provision
```

A CU endpoint configured in a shared CU profile can also be reused:

```bash
az cu profile set --key endpoint --value https://<resource-name>.services.ai.azure.com/
az cu analyzer list
```

Use standard Azure CLI output and query options:

```bash
az cu analyzer list --kind prebuilt --output table
az cu analyzer list --query "[?analyzerId=='prebuilt-layout']"
```

Analyzer definitions can be created and deleted with native Azure CLI confirmation:

```bash
az cu analyzer create --name ContosoInvoice --schema analyzer.json
az cu analyzer delete --name ContosoInvoice
az cu analyzer delete --name ContosoInvoice --yes
```

Resource model-deployment defaults can be merged or replaced:

```bash
az cu defaults set --model gpt-5.2=gpt52 --model text-embedding-3-large=embedding3
az cu defaults set --model gpt-5.2=gpt52 --replace
```

Preview 2 and Preview 3 capabilities include:

```bash
az cu analyzer validate --schema analyzer.json --spec
az cu analyzer schema create --name ContosoInvoice --output-file analyzer.json
az cu analyzer test --name ContosoInvoice --source samples --output-file report.json --yes
az cu profile create --name dev
az cu profile copy --source dev --destination prod
az cu profile set-active --name prod
az cu analyzer copy --source ContosoInvoice --destination ContosoInvoice_v2
az cu doctor
az cu env-var list
```

Remote inputs use explicit repeatable `--url` options. Azure Blob SAS query
parameters are passed to the service but redacted from errors and reports.
Large batches require native Azure CLI confirmation unless `--yes` is supplied.
Analyzer and profile deletion also use native confirmation.

`az cu infra generate` writes a self-contained azd/Bicep project and never runs
`azd up` or provisions resources itself. On a terminal it offers subscription,
resource, region, model, and RBAC choices; use `--yes` for deterministic
automation. Generated hooks use the underscore-prefixed internal
`az cu _infra-models` helper and do not require the standalone `cu-cli` package.

This extension intentionally does not register direct provisioning or
self-upgrade. Update it with `az extension update --name content-understanding`.

The runtime does not import or depend on the standalone `cu_cli` package,
Click, Rich, updater code, or standalone provisioning code. The extension wheel
contains a build-time snapshot of the repository's canonical azd/Bicep template.
Microsoft Entra authentication always uses the active Azure CLI host credential;
the preview explicitly supports AzureCloud only.

> [!IMPORTANT]
> This package is an implementation preview. The `az cu` command name and public
> Azure CLI extension registration remain subject to Azure CLI maintainer review.
