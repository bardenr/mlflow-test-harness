"""Test mlflow_test_harness.__main__"""

from mlflow_test_harness.__main__ import cli


class TestCli:
    """TestDeleteMe"""

    @staticmethod
    def test_cli() -> None:
        """test_cli"""

        assert cli() == 0
