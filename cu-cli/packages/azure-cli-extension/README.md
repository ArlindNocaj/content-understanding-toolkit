# Azure Content Understanding extension for Azure CLI

This preview extension adds Azure Content Understanding commands under `az cu`.

The initial vertical slice supports listing analyzers with the identity and active
subscription selected by Azure CLI:

```bash
az login
az cu analyzer list --endpoint https://<resource-name>.services.ai.azure.com/
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

> [!IMPORTANT]
> This package is an implementation preview. The `az cu` command name and public
> Azure CLI extension registration remain subject to Azure CLI maintainer review.
