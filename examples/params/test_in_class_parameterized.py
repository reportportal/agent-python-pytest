"""A simple example test in a class with a parameter."""
import pytest


class Tests:

    @pytest.mark.parametrize('param', ['param'])
    def test_in_class_parameterized(self, param):
        """
        This is my test inside `Tests` class with a parameter
        """
        assert True
