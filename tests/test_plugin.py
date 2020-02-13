"""This modules includes unit tests for the plugin."""

try:
    from unittest.mock import create_autospec, Mock, patch
except ImportError:
    from mock import create_autospec, Mock, patch

from _pytest.config import Config
from delayed_assert import expect, assert_expectations
import pytest
from requests.exceptions import RequestException

from pytest_reportportal.listener import RPReportListener
from pytest_reportportal.plugin import pytest_configure, pytest_sessionfinish
from pytest_reportportal.service import PyTestServiceClass
from pytest_reportportal import RPLogger


@pytest.fixture
def logger():
    return RPLogger("pytest_reportportal.test")


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


@patch('pytest_reportportal.RPLogger.handle')
@pytest.mark.parametrize("log_level", ("info", "debug", "warning", "error"))
def test_logger_handle_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels with some text attachment."""
    log_call = getattr(logger, log_level)
    attachment = "Some {} attachment".format(log_level)
    log_call("Some {} message".format(log_level), attachment=attachment)
    expect(mock_handler.call_count == 1, "logger.handle called more than 1 time")
    expect(getattr(mock_handler.call_args[0][0], "attachment") == attachment,
           "record.attachment in args doesn't match real value")
    assert_expectations()


@patch('pytest_reportportal.RPLogger.handle')
@pytest.mark.parametrize("log_level", ("info", "debug", "warning", "error"))
def test_logger_handle_no_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels without any attachment."""
    log_call = getattr(logger, log_level)
    log_call("Some {} message".format(log_level))
    expect(mock_handler.call_count == 1, "logger.handle called more than 1 time")
    expect(getattr(mock_handler.call_args[0][0], "attachment") is None,
           "record.attachment in args is not None")
    assert_expectations()


def test_pytest_runtest_protocol(request):
    """Test listener pytest_runtest_protocol hook."""
    rp_service = Mock()
    rp_service.is_item_update_supported = Mock(return_value=False)
    rp_listener = RPReportListener(rp_service)
    rp_listener._add_issue_id_marks = Mock()
    test_item = Mock()

    next(rp_listener.pytest_runtest_protocol(test_item))

    expect(rp_listener._add_issue_id_marks.call_count == 1,
            "_add_issue_id_marks called more than 1 time")
    assert_expectations()


@patch('reportportal_client.service.ReportPortalService.get_project_settings')
def test_is_item_update_supported(request):
    """Test listener public is_client_support_item_update method."""
    func = None
    rp_service = PyTestServiceClass()
    rp_service.init_service("endpoint", "project", "uuid", 20, False, [], True)

    if hasattr(rp_service.RP, "update_test_item"):
        rp_service.RP.supported_methods.remove("update_test_item")
        func = rp_service.RP.update_test_item
        delattr(type(rp_service.RP), "update_test_item")


    result = rp_service.is_item_update_supported()
    expect(result == False,
           "incorrect result for is_client_support_item_update method")

    rp_service.RP.update_test_item = func
    rp_service.RP.supported_methods.append("update_test_item")

    result = rp_service.is_item_update_supported()
    expect(result == True,
           "incorrect result for is_client_support_item_update method")
    assert_expectations()


def test_add_issue_info(request):
    """Test listener helper _add_issue_info method."""
    rp_service = Mock()
    rp_listener = RPReportListener(rp_service)
    rp_service.issue_types = {"TST": "TEST"}

    report = Mock()
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

    test_item = Mock()
    test_item.session.config.getini = getini
    test_item.iter_markers = iter_markers

    rp_listener._add_issue_info(test_item, report)

    expect(rp_listener.issue['issue_type'] == "TEST",
           "incorrect test issue_type")
    expect(rp_listener.issue['comment'] == "* issue: [456823](https://bug.com/456823)",
           "incorrect test comment")
    assert_expectations()


def test_add_issue_id_marks(request):
    """Test listener helper _add_issue_id_marks method."""
    rp_service = Mock()
    rp_listener = RPReportListener(rp_service)

    def getini(option):
        if option == "rp_issue_id_marks":
            return True
        elif option == "rp_issue_marks":
            return ["issue"]
        return None

    def iter_markers(name=None):
        for mark in [pytest.mark.issue(issue_id="456823")]:
            yield mark

    test_item = Mock()
    test_item.session.config.getini = getini
    test_item.iter_markers = iter_markers

    rp_listener._add_issue_id_marks(test_item)

    expect(test_item.add_marker.call_count == 1,
           "item.add_marker called more than 1 time")
    expect(test_item.add_marker.call_args[0][0] == "issue:456823",
           "item.add_marker called with incorrect parameters")
    assert_expectations()


@patch('pytest_reportportal.plugin.is_master', Mock(return_value=True))
@pytest.mark.parametrize('shouldfail, outcome', [
    (False, False), ('stopping after 1 failures', True)
])
def test_sessionfinish_with_maxfail(shouldfail, outcome):
    """Test session_finish logic when the maxfail Pytest argument is in use.

    :param shouldfail: shouldfail attribute value for the Session object
    :param outcome:    nowait argument value passed to the terminate_service()
    """
    mocked_session = Mock()
    mocked_session.shouldfail = shouldfail
    mocked_session.config = Mock()
    mocked_session.config._reportportal_configured = True
    mocked_session.config.py_test_service.terminate_service = Mock()
    mocked_session.config.py_test_service.finish_launch = Mock()
    pytest_sessionfinish(mocked_session)
    expect(lambda: mocked_session.config.py_test_service.
        finish_launch.assert_called_with(force=outcome, status='RP_Launch'))
    expect(lambda: mocked_session.config.py_test_service.
        terminate_service.assert_called_with(nowait=outcome))
    assert_expectations()
