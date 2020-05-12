"""This modules includes unit tests for the service.py module."""

from six.moves import mock

from delayed_assert import expect, assert_expectations
import pytest


def test_item_attributes(rp_service):
    """Test that item attributes are generated in a supported way."""
    rp_service.is_item_update_supported = mock.Mock(return_value=False)

    def getini(option):
        if option == 'rp_tests_attributes':
            return ['ini_marker']

    def get_closest_marker(name):
        return {'test_marker': pytest.mark.test_marker}.get(name)

    class NodeKeywords(object):
        _keywords = ['pytestmark', 'ini_marker', 'test_marker']

        def __iter__(self):
            return iter(self._keywords)

    test_item = mock.Mock()
    test_item.session.config.getini = getini
    test_item.keywords = NodeKeywords()
    test_item.get_closest_marker = get_closest_marker
    markers = rp_service._get_item_markers(test_item)
    assert markers == [{'value': 'test_marker'}, {'value': 'ini_marker'}]


def test_get_item_parameters(rp_service):
    """Test that parameters are returned in a way supported by the client."""
    test_item = mock.Mock()
    test_item.callspec.params = {'param': 'param_value'}

    expect(rp_service._get_parameters(test_item) == {'param': 'param_value'})

    delattr(test_item, 'callspec')
    expect(rp_service._get_parameters(test_item) is None)

    assert_expectations()
