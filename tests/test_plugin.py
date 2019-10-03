"""This modules includes unit tests for the plugin."""

from requests.exceptions import RequestException
try:
    from unittest.mock import create_autospec, Mock, patch
except ImportError:
    from mock import create_autospec, Mock, patch

from _pytest.config import Config
from  delayed_assert import expect, assert_expectations

from pytest_reportportal.plugin import pytest_configure


@patch('pytest_reportportal.plugin.requests.get')
def test_stop_plugin_configuration_on_conn_error(mocked_get):
    """Test plugin configuration in case of HTTP error.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be change to False, stopping plugin configuration, if HTTP
    error occurs getting HTTP response from the ReportPortal.
    :param mocked_get: Instance of the MagicMock
    """
    mocked_config = create_autospec(Config)
    mocked_config.return_value._reportportal_configured = True
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = RequestException()
    mocked_get.return_value = mock_response
    expect(pytest_configure(mocked_config) is None,
           'Received unexpected return value from pytest_configure.')
    expect(mocked_config._reportportal_configured is False,
           'The value of the _reportportal_configured is not False.')
    assert_expectations()
