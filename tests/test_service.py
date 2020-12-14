"""This modules includes unit tests for the service.py module."""

from six.moves import mock

from delayed_assert import expect, assert_expectations
import pytest


def test_item_attributes(mocked_item, rp_service):
    """Test that item attributes are generated in a supported way."""
    rp_service.is_item_update_supported = mock.Mock(return_value=False)

    def getini(option):
        if option == 'rp_tests_attributes':
            return ['ini_marker', 'test_ini_key:test_ini_value']

    def get_closest_marker(name):
        return {'test_marker': pytest.mark.test_marker,
                'test_decorator_key':
                    pytest.mark.test_decorator_key('test_decorator_value'),
                'test_decorator_key_with_multi_value':
                    pytest.mark.test_decorator_key_with_multi_value(
                        'test_value1', 'test_value2')
                }.get(name)

    class NodeKeywords(object):
        _keywords = ['pytestmark',
                     'ini_marker',
                     'test_marker',
                     'test_decorator_key',
                     'test_decorator_key_with_multi_value',
                     'test_ini_key']

        def __iter__(self):
            return iter(self._keywords)

    mocked_item.session.config.getini = getini
    mocked_item.keywords = NodeKeywords()
    mocked_item.get_closest_marker = get_closest_marker
    markers = rp_service._get_item_markers(mocked_item)
    assert markers == [{'value': 'test_marker'},
                       {'key': 'test_decorator_key',
                        'value': 'test_decorator_value'},
                       {'key': 'test_decorator_key_with_multi_value',
                        'value': 'test_value1'},
                       {'key': 'test_decorator_key_with_multi_value',
                        'value': 'test_value2'},
                       {'value': 'ini_marker'},
                       {'key': 'test_ini_key',
                        'value': 'test_ini_value'}]


def test_get_item_parameters(mocked_item, rp_service):
    """Test that parameters are returned in a way supported by the client."""
    mocked_item.callspec.params = {'param': 'param_value'}

    expect(rp_service._get_parameters(mocked_item) == {'param': 'param_value'})

    delattr(mocked_item, 'callspec')
    expect(rp_service._get_parameters(mocked_item) is None)

    assert_expectations()


@mock.patch('reportportal_client.service.ReportPortalService.start_test_item')
def test_code_ref_bypass(mocked_item_start, mocked_item, mocked_session,
                         rp_service):
    """ Test that a test code reference constructed and bypassed to a client.

    :param mocked_item_start: mocked start_test_item method reference
    :param mocked_item:       a mocked test item
    :param mocked_session:    a mocked test session
    :param rp_service:        an instance of
                              reportportal_client.service.ReportPortalService
    """
    ini = {
        'rp_hierarchy_parametrize': False,
        'rp_hierarchy_dirs': False,
        'rp_hierarchy_module': True,
        'rp_hierarchy_class': True,
        'rp_display_suite_test_file': True,
        'rp_hierarchy_dirs_level': 0,
        'rp_tests_attributes': [],
        'norecursedirs': ['.*', 'build', 'dist', 'CVS', '_darcs', '{arch}',
                          '*.egg', 'venv']
    }

    def get_closest_marker(name):
        return {'test_marker': pytest.mark.test_marker}.get(name)

    class NodeKeywords(object):
        _keywords = ['pytestmark', 'ini_marker', 'test_marker']

        def __iter__(self):
            return iter(self._keywords)

    mocked_item.session.config.getini = lambda x: ini[x]
    mocked_item.keywords = NodeKeywords()
    mocked_item.get_closest_marker = get_closest_marker
    mocked_item.callspec.params = None

    mocked_session.items = [mocked_item]

    rp_service.collect_tests(mocked_session)
    rp_service.start_pytest_item(mocked_item)

    expect(mocked_item_start.call_count == 1, 'One HTTP POST sent')
    code_ref = mocked_item_start.call_args[1]['code_ref']
    expect(code_ref == '/path/to/test:test_item')
    assert_expectations()
