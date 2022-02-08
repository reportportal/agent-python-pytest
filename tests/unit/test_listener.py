"""This modules includes unit tests for the listener."""
from _pytest.mark import MarkDecorator
from six.moves import mock

from delayed_assert import expect, assert_expectations
import pytest

from pytest_reportportal.listener import RPReportListener


def test_pytest_runtest_protocol(mocked_item):
    """Test listener pytest_runtest_protocol hook.

    :param mocked_item: Pytest fixture
    """
    rp_service = mock.Mock()
    rp_service.issue_types = {}
    rp_listener = RPReportListener(rp_service)
    rp_listener._add_issue_id_attribute = mock.Mock()
    mocked_item.iter_markers = lambda name: []

    next(rp_listener.pytest_runtest_protocol(mocked_item))

    expect(rp_listener._add_issue_id_attribute.call_count == 1,
           '_add_issue_id_marks called more than 1 time')
    assert_expectations()


def test_get_issue_info(rp_listener, rp_service):
    """Test listener helper _get_issue_info method.

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

    marks = rp_listener._process_issue_marks(test_item)
    issue = rp_listener._get_issue_info(test_item, marks)

    expect(issue.issue_type == "TEST",
           "incorrect test issue_type")
    expect(issue.comment ==
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

    marks = rp_listener._process_issue_marks(mocked_item)
    rp_listener._add_issue_id_attribute(mocked_item, marks)

    assert mocked_item.add_marker.call_count == 1,\
        "item.add_marker called more than 1 time"
    mark = mocked_item.add_marker.call_args[0][0]
    expect(isinstance(mark, MarkDecorator))
    expect(mark.name == "issue",
           "incorrect mark name: {}".format(str(mark.name)))
    expect(mark.args[0] == "456823",
           "incorrect mark args: {}".format(str(mark.args)))
    assert_expectations()
