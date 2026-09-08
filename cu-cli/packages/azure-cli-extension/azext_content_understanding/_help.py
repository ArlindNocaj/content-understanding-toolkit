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
