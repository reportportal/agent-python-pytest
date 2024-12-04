"""A simple example test with different parameter types."""
import pytest


BINARY_TEXT = 'Some text with binary symbol \0'


@pytest.mark.parametrize(
    ['text'], [[BINARY_TEXT]]
)
def test_in_class_parameterized(text):
    """
    This is my test with different parameter types.
    """
    assert text == BINARY_TEXT
    assert text != BINARY_TEXT.replace('\0', '\\0')
