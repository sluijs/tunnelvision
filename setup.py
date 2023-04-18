#!/usr/bin/env python

import os
import subprocess
import sys
from shutil import rmtree

from setuptools import Command, find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def get_version():
    init_py_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "tunnelvision", "__init__.py"
    )
    init_py = open(init_py_path, "r").readlines()
    version_line = [l.strip() for l in init_py if l.startswith("__version__")][0]  # noqa: E741
    version = version_line.split("=")[-1].strip().strip("'\"")

    # The following is used to build release packages.
    # Users should never use it.
    suffix = os.getenv("TUNNELVISION_VERISON_SUFFIX", "")
    version = version + suffix
    if os.getenv("BUILD_NIGHTLY", "0") == "1":
        from datetime import datetime

        date_str = datetime.today().strftime("%y%m%d")
        version = version + ".dev" + date_str

        new_init_py = [l for l in init_py if not l.startswith("__version__")]  # noqa: E741
        new_init_py.append('__version__ = "{}"\n'.format(version))
        with open(init_py_path, "w") as f:
            f.write("".join(new_init_py))
    return version


class UploadCommand(Command):
    """Support setup.py upload.

    Only run upload from the main branch.

    Adapted from https://github.com/robustness-gym/meerkat.
    """

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Only upload from the main branch
        branches = subprocess.getoutput("git branch").split("\n")
        branches = [x.strip() for x in branches]
        curr_branch = [x for x in branches if x.startswith("*")]
        if len(curr_branch) != 1:
            raise RuntimeError("Could not determine current branch.")
        curr_branch = curr_branch[0].split(" ")[-1]
        if curr_branch != "main":
            raise RuntimeError("Uploads only allowed from main branch.")

        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(get_version()))
        os.system("git push --tags")

        sys.exit()


# ---------------------------------------------------
# Setup Information
# ---------------------------------------------------

# Required packages
REQUIRED = [
    "dataclasses>=0.6",
    "numpy",
    "packaging",
    "PyYAML>=5.4.1",
    "tabulate",
    "termcolor",
    "websockets",
    "shortuuid",
]

# Optional packages
EXTRAS = {
    "dev": [
        # optional dependency libraries
        # formatting
        "coverage",
        "flake8",
        "flake8-bugbear",
        "flake8-comprehensions",
        "isort",
        "black==22.8.0",
        "click==8.0.2",
        # testing
        "pytest-cov>=2.10.1",
        "pre-commit>=2.9.3",
        "parameterized",
        # upload
        "twine",
    ],
    "docs": ["mistune>=0.8.1,<2.0.0", "sphinx", "sphinxcontrib.bibtex", "m2r2"],
}

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name="tunnelvision",
    version=get_version(),
    author="Rogier van der Sluijs",
    url="https://github.com/sluijs/tunnelvision",
    project_urls={"Documentation": "https://tunnelvision.readthedocs.io/"},
    description="Experimental tensor viewer for IPython built on top of Voxel",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("configs", "tests", "tests.*")),
    package_data={"tunnelvision": ["bin/**/*"]},
    python_requires=">=3.6",
    install_requires=REQUIRED,
    license="GNU",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    extras_require=EXTRAS,
    # $ setup.py publish support.
    cmdclass={
        "upload": UploadCommand,
    },
)
