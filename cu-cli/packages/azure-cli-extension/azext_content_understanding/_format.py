# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI table projections for Content Understanding results."""

from __future__ import annotations

from typing import Any


def analyzer_list_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project analyzer results into stable table columns without changing JSON output."""

    return [
        {
            "AnalyzerId": item.get("analyzerId"),
            "Description": item.get("description"),
            "CreatedAt": item.get("createdAt"),
            "LastModifiedAt": item.get("lastModifiedAt"),
        }
        for item in results
    ]
