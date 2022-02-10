"""A simple example test in a class with a parameter."""
import pytest


@pytest.mark.parametrize(
    ['integer', 'floating_point', 'boolean', 'none'], [(1, 1.5, True, None)]
)
def test_in_class_parameterized(integer, floating_point, boolean, none):
    """
    This is my test inside `Tests` class with a parameter
    """
    assert True
