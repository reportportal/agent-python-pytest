"""This modules includes unit tests for helpers."""

from pytest_reportportal.helpers import get_attributes


def test_get__attributes():
    """Test get_attributes functionality."""
    expected_out = [{'value': 'Tag'}, {'key': 'Key', 'value': 'Value'}]
    out = get_attributes(['Tag', 'Key:Value', ''])
    assert expected_out == out
