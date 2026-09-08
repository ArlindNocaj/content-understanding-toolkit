# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Translate frontend-neutral CU failures into Azure CLI errors."""

from __future__ import annotations

from azure.cli.core.azclierror import (
    ArgumentUsageError,
    AuthenticationError as AzureCliAuthenticationError,
    AzureConnectionError,
    InvalidArgumentValueError,
    ResourceNotFoundError,
)
from knack.util import CLIError

from cu_cli_core.errors import CuCoreError, ErrorCategory


def azure_cli_error(error: CuCoreError) -> CLIError:
    """Create an Azure CLI error while preserving safe CU diagnostic context."""

    message = error.message
    if error.hint:
        message = f"{message} {error.hint}"

    error_types = {
        ErrorCategory.USAGE: ArgumentUsageError,
        ErrorCategory.VALIDATION: InvalidArgumentValueError,
        ErrorCategory.AUTHENTICATION: AzureCliAuthenticationError,
        ErrorCategory.NOT_FOUND: ResourceNotFoundError,
        ErrorCategory.LOCAL_IO: AzureConnectionError,
    }
    error_type = error_types.get(error.category, CLIError)
    return error_type(message)
