#!/usr/bin/env python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path

from setuptools import find_packages, setup

VERSION = "0.1.0b1"
ROOT = Path(__file__).parent

setup(
    name="content-understanding",
    version=VERSION,
    description="Azure CLI extension for Azure Content Understanding.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Microsoft Corporation",
    url="https://github.com/Azure/content-understanding-toolkit/tree/main/cu-cli",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "cu-cli-core>=0.1.0b2,<0.2.0",
        "azure-mgmt-cognitiveservices>=13.6.0,<14.0.0",
    ],
    extras_require={
        "dev": [
            "azure-cli-core>=2.75.0",
            "build>=1.2",
            "mypy>=1.8,<2",
            "pytest>=7.4",
            "ruff>=0.5,<0.16",
        ]
    },
    package_data={"azext_content_understanding": ["azext_metadata.json"]},
)
