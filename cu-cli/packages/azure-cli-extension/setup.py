#!/usr/bin/env python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path
import shutil

from setuptools.command.build_py import build_py
from setuptools import setup

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
    cmdclass={"build_py": BuildPyWithInfraTemplate},
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
