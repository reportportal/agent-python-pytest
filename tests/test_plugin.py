"""This modules includes unit tests for the plugin."""

from six.moves import mock
import os

from delayed_assert import expect, assert_expectations
import pytest
from requests.exceptions import RequestException

from pytest_reportportal.plugin import (
    get_launch_attributes,
    pytest_configure,
    pytest_sessionstart,
    is_portal_on_maintenance
)


@mock.patch('pytest_reportportal.plugin.requests.get')
def test_stop_plugin_configuration_on_conn_error(mocked_get, mocked_config):
    """Test plugin configuration in case of HTTP error.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be changed to False, stopping plugin configuration, if HTTP
    error occurs getting HTTP response from the ReportPortal.
    :param mocked_get:    Instance of the MagicMock
    :param mocked_config: Pytest fixture
    """
    mock_response = mock.Mock()
    mock_response.raise_for_status.side_effect = RequestException()
    mocked_get.return_value = mock_response
    expect(pytest_configure(mocked_config) is None,
           'Received unexpected return value from pytest_configure.')
    expect(mocked_config._reportportal_configured is False,
           'The value of the _reportportal_configured is not False.')
    assert_expectations()


@mock.patch('pytest_reportportal.RPLogger.handle')
@pytest.mark.parametrize('log_level', ('info', 'debug', 'warning', 'error'))
def test_logger_handle_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels with some text attachment."""
    log_call = getattr(logger, log_level)
    attachment = 'Some {} attachment'.format(log_level)
    log_call("Some {} message".format(log_level), attachment=attachment)
    expect(mock_handler.call_count == 1,
           'logger.handle called more than 1 time')
    expect(getattr(mock_handler.call_args[0][0], "attachment") == attachment,
           'record.attachment in args doesn\'t match real value')
    assert_expectations()


@mock.patch('pytest_reportportal.RPLogger.handle')
@pytest.mark.parametrize('log_level', ('info', 'debug', 'warning', 'error'))
def test_logger_handle_no_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels without any attachment."""
    log_call = getattr(logger, log_level)
    log_call('Some {} message'.format(log_level))
    expect(mock_handler.call_count == 1,
           'logger.handle called more than 1 time')
    expect(getattr(mock_handler.call_args[0][0], 'attachment') is None,
           'record.attachment in args is not None')
    assert_expectations()


@mock.patch.dict(os.environ, {'RP_UUID': 'foobar'})
def test_uuid_env_var_override(mocked_session):
    """
    Test setting RP_UUID env variable overrides the rp_uuid config value.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.py_test_service = mock.Mock()
    mocked_session.config.option = mock.Mock()
    mocked_session.config.pluginmanager = mock.Mock()
    mocked_session.config.py_test_service.init_service = mock.Mock()
    pytest_sessionstart(mocked_session)
    args, kwargs = mocked_session.config.py_test_service.init_service.call_args
    assert kwargs.get('uuid') == 'foobar'


def test_get_launch_attributes():
    """Test get_launch_attributes functionality."""
    expected_out = [{'value': 'Tag'}, {'key': 'Key', 'value': 'Value'}]
    out = get_launch_attributes(['Tag', 'Key:Value', ''])
    assert expected_out == out


@mock.patch('pytest_reportportal.plugin.requests.get')
def test_portal_on_maintenance(mocked_get, mocked_session):
    """Test if portal on maintenance."""
    mock_response = mock.Mock()
    mock_response.text = "<title>Report Portal - Maintenance</title>"
    mocked_get.return_value = mock_response
    mocked_session.config.getini = mock.Mock()

    assert is_portal_on_maintenance(mocked_session)


@mock.patch('pytest_reportportal.plugin.requests.get')
def test_portal_not_on_maintenance(mocked_get, mocked_session):
    """Test if portal not on maintenance."""
    mock_response = mock.Mock()
    mock_response.text = "{'project':2,'subTypes':'foobar'}"
    mocked_get.return_value = mock_response
    mocked_session.config.getini = mock.Mock()

    assert not is_portal_on_maintenance(mocked_session)
