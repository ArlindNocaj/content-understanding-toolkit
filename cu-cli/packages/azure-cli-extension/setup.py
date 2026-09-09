#!/usr/bin/env python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path
import shutil

from setuptools.command.build_py import build_py
from setuptools import find_packages, setup

VERSION = "0.1.0b1"
ROOT = Path(__file__).parent
TEMPLATE_SOURCE = ROOT.parent / "standalone" / "src" / "cu_cli" / "resources" / "azd_template"


class BuildPyWithInfraTemplate(build_py):
    """Copy the canonical azd template into the built extension package."""

    def run(self):
        super().run()
        destination = Path(self.build_lib) / "azext_content_understanding" / "_infra_template"
        if not TEMPLATE_SOURCE.is_dir():
            raise RuntimeError(f"infrastructure template source not found: {TEMPLATE_SOURCE}")
        shutil.copytree(TEMPLATE_SOURCE, destination, dirs_exist_ok=True)

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
    cmdclass={"build_py": BuildPyWithInfraTemplate},
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
    package_data={
        "azext_content_understanding": [
            "azext_metadata.json",
            "_infra_overrides/*",
            "_infra_template/*",
            "_infra_template/infra/*",
            "_infra_template/infra/modules/*",
            "_infra_template/hooks/*",
        ]
    },
)
