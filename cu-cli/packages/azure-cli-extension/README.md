# Azure Content Understanding extension for Azure CLI

This preview extension adds Azure Content Understanding commands under `az cu`.

The initial preview supports analyzer management, one-file analysis, and Content
Understanding defaults with the identity and active subscription selected by Azure CLI:

```bash
az login
az cu analyzer list --endpoint https://<resource-name>.services.ai.azure.com/
az cu analyzer show --name prebuilt-invoice
az cu analyze --file invoice.pdf --analyzer-name prebuilt-invoice
az cu defaults show --output table
```

A CU endpoint configured by the standalone CU CLI can also be reused:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
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

The initial preview accepts one local file per `az cu analyze` invocation. URL and
batch inputs are planned for later preview updates.

> [!IMPORTANT]
> This package is an implementation preview. The `az cu` command name and public
> Azure CLI extension registration remain subject to Azure CLI maintainer review.
