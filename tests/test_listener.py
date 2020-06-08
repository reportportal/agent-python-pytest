"""This modules includes unit tests for the listener."""

from six.moves import mock

from delayed_assert import expect, assert_expectations
import pytest

from pytest_reportportal.listener import RPReportListener


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
