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
    ServiceError as AzureCliServiceError,
)
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError as AzureResourceNotFoundError,
    ServiceRequestError,
)
from knack.util import CLIError

from cu_cli_core.errors import CuCoreError, ErrorCategory

TRANSLATABLE_ERRORS = (
    CuCoreError,
    ClientAuthenticationError,
    AzureResourceNotFoundError,
    ServiceRequestError,
    HttpResponseError,
)


def azure_cli_error(error: Exception) -> CLIError:
    """Create an Azure CLI error while preserving safe CU diagnostic context."""

    if isinstance(error, CuCoreError):
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

    message = getattr(error, "message", None) or str(error)
    if isinstance(error, ClientAuthenticationError):
        return AzureCliAuthenticationError(message)
    if isinstance(error, AzureResourceNotFoundError):
        return ResourceNotFoundError(message)
    if isinstance(error, ServiceRequestError):
        return AzureConnectionError(message)
    if isinstance(error, HttpResponseError):
        if error.status_code in {401, 403}:
            return AzureCliAuthenticationError(message)
        if error.status_code == 404:
            return ResourceNotFoundError(message)
        if error.status_code == 400:
            return InvalidArgumentValueError(message)
        return AzureCliServiceError(message)
    return CLIError(message)
