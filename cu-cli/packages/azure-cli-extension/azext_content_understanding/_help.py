# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Help text for the Content Understanding extension."""

from knack.help_files import helps

helps["cu"] = """
    type: group
    short-summary: Manage and use Azure Content Understanding.
"""

helps["cu analyzer"] = """
    type: group
    short-summary: Manage Content Understanding analyzers.
"""

helps["cu analyzer list"] = """
    type: command
    short-summary: List analyzers in a Microsoft Foundry resource.
    examples:
      - name: List all analyzers by using an explicit endpoint.
        text: az cu analyzer list --endpoint https://contoso.services.ai.azure.com/
      - name: List prebuilt analyzers using the endpoint from the active CU profile.
        text: az cu analyzer list --kind prebuilt --output table
      - name: Select an analyzer with a JMESPath query.
        text: az cu analyzer list --query "[?analyzerId=='prebuilt-layout']"
"""

helps["cu analyzer show"] = """
    type: command
    short-summary: Show an analyzer definition.
    examples:
      - name: Show an analyzer.
        text: az cu analyzer show --name prebuilt-layout --endpoint https://contoso.services.ai.azure.com/
      - name: Return only the analyzer description.
        text: az cu analyzer show --name prebuilt-layout --query description --output tsv
"""

helps["cu analyzer create"] = """
    type: command
    short-summary: Create an analyzer from a local JSON schema.
    examples:
      - name: Create a custom analyzer.
        text: az cu analyzer create --name ContosoInvoice --schema analyzer.json --endpoint https://contoso.services.ai.azure.com/
"""

helps["cu analyzer delete"] = """
    type: command
    short-summary: Delete an analyzer.
    examples:
      - name: Confirm and delete an analyzer.
        text: az cu analyzer delete --name ContosoInvoice
      - name: Delete an analyzer without prompting.
        text: az cu analyzer delete --name ContosoInvoice --yes
"""

helps["cu analyze"] = """
    type: command
    short-summary: Analyze one local file with Content Understanding.
    examples:
      - name: Analyze an invoice with an explicit analyzer and endpoint.
        text: az cu analyze --file invoice.pdf --analyzer-name prebuilt-invoice --endpoint https://contoso.services.ai.azure.com/
      - name: Analyze a file using defaults from the active CU profile.
        text: az cu analyze --file invoice.pdf
      - name: Select extracted fields using JMESPath.
        text: az cu analyze --file invoice.pdf --query "contents[0].fields"
"""

helps["cu defaults"] = """
    type: group
    short-summary: Manage Content Understanding model-deployment defaults.
"""

helps["cu defaults show"] = """
    type: command
    short-summary: Show Content Understanding model-deployment defaults.
    examples:
      - name: Show defaults as JSON.
        text: az cu defaults show --endpoint https://contoso.services.ai.azure.com/
      - name: Show defaults as a table.
        text: az cu defaults show --output table
"""

helps["cu defaults set"] = """
    type: command
    short-summary: Configure Content Understanding model-deployment defaults.
    examples:
      - name: Add or update model deployment mappings.
        text: az cu defaults set --model gpt-5.2=gpt52 --model text-embedding-3-large=embedding3
      - name: Replace all model deployment mappings.
        text: az cu defaults set --model gpt-5.2=gpt52 --replace
"""
