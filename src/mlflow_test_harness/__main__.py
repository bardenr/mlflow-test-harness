"""__main__"""

import sys

from mlflow_test_harness import __version__

WELCOME_MESSAGE = """
Hello! This is a default command line entry point for mlflow_test_harness. When this package is installed, this module
allows you to invoke the cli by running:

    python -m mlflow_test_harness

If you would like setuptools to automatically create an executable cli wrapper, see the relevant setuptools docs on how
to configure this in the pyproject.toml

If you don't want your package to have a CLI simply delete this file. I won't mind.
"""


def cli() -> int:
    """Default Command Line Interface"""

    print(f"mlflow_test_harness {__version__}")
    print(WELCOME_MESSAGE)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
