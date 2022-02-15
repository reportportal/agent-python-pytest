"""This modules includes unit tests for the service.py module."""

import pytest
from delayed_assert import expect, assert_expectations
from six.moves import mock

from tests import REPORT_PORTAL_SERVICE


def test_get_item_parameters(mocked_item, rp_service):
    """Test that parameters are returned in a way supported by the client."""
    mocked_item.callspec.params = {'param': 'param_value'}

    expect(rp_service._get_parameters(mocked_item) == {'param': 'param_value'})

    delattr(mocked_item, 'callspec')
    expect(rp_service._get_parameters(mocked_item) is None)

    assert_expectations()
