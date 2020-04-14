"""This modules includes unit tests for the plugin."""

from six.moves import mock

from delayed_assert import expect, assert_expectations
import pytest
from requests.exceptions import RequestException

from pytest_reportportal.listener import RPReportListener
from pytest_reportportal.plugin import pytest_configure


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


def test_pytest_runtest_protocol(mocked_item):
    """Test listener pytest_runtest_protocol hook.

    :param mocked_item: Pytest fixture
    """
    rp_service = mock.Mock()
    rp_service.is_item_update_supported = mock.Mock(return_value=False)
    rp_listener = RPReportListener(rp_service)
    rp_listener._add_issue_id_marks = mock.Mock()

    next(rp_listener.pytest_runtest_protocol(mocked_item))

    expect(rp_listener._add_issue_id_marks.call_count == 1,
           '_add_issue_id_marks called more than 1 time')
    assert_expectations()


def test_add_issue_info(rp_listener, rp_service):
    """Test listener helper _add_issue_info method.

    :param rp_listener: Pytest fixture
    :param rp_service:  Pytest fixture
    """
    rp_service._issue_types = {"TST": "TEST"}

    report = mock.Mock()
    report.when = "call"
    report.skipped = False

    def getini(option):
        if option == "rp_issue_system_url":
            return "https://bug.com/{issue_id}"
        elif option == "rp_issue_marks":
            return ["issue"]
        return None

    def iter_markers(name=None):
        for mark in [pytest.mark.issue(issue_id="456823", issue_type="TST")]:
            yield mark

    test_item = mock.Mock()
    test_item.session.config.getini = getini
    test_item.iter_markers = iter_markers

    rp_listener._add_issue_info(test_item, report)

    expect(rp_listener.issue['issueType'] == "TEST",
           "incorrect test issue_type")
    expect(rp_listener.issue['comment'] ==
           "* issue: [456823](https://bug.com/456823)",
           "incorrect test comment")
    assert_expectations()


def test_add_issue_id_marks(rp_listener, mocked_item):
    """Test listener helper _add_issue_id_marks method.

    :param rp_listener: Pytest fixture
    :param mocked_item: Pytest fixture
    """
    def getini(option):
        if option == "rp_issue_id_marks":
            return True
        elif option == "rp_issue_marks":
            return ["issue"]
        return None

    def iter_markers(name=None):
        for mark in [pytest.mark.issue(issue_id="456823")]:
            yield mark

    mocked_item.session.config.getini = getini
    mocked_item.iter_markers = iter_markers

    rp_listener._add_issue_id_marks(mocked_item)

    expect(mocked_item.add_marker.call_count == 1,
           "item.add_marker called more than 1 time")
    expect(mocked_item.add_marker.call_args[0][0] == "issue:456823",
           "item.add_marker called with incorrect parameters")
    assert_expectations()
