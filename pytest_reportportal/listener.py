"""RPReportListener implements Pytest hooks required for item reporting."""

import logging

import pytest
from reportportal_client.core.rp_issues import Issue

try:
    # noinspection PyCompatibility
    from html import escape  # python3
except ImportError:
    from cgi import escape  # python2

import _pytest.logging
from .rp_logging import RPLogHandler, patching_logger_class

NOT_ISSUE = Issue('NOT_ISSUE')


class RPReportListener(object):
    """RPReportListener class."""

    def __init__(self, py_test_service,
                 log_level=logging.NOTSET,
                 endpoint=None):
        """Initialize RPReport Listener instance.

        :param py_test_service: PyTestServiceClass instance
        :param log_level:       One of the 'CRITICAL', 'ERROR',
                                'WARNING','INFO','DEBUG', 'NOTSET'
        :param endpoint:        Report Portal API endpoint
        """
        # Test Item result
        self.py_test_service = py_test_service
        self.results = {}
        self.issues = {}
        self._log_level = log_level
        self._log_handler = \
            RPLogHandler(py_test_service=py_test_service,
                         level=log_level,
                         filter_client_logs=True,
                         endpoint=endpoint)

    # noinspection PyMethodMayBeStatic
    def _process_issue_marks(self, item):
        issue_marks = [mark for mark in item.iter_markers(name='issue') if
                       mark]
        # Remove useless `issue` attributes
        [item.own_markers.remove(mark) for mark in issue_marks]
        return issue_marks

    # noinspection PyMethodMayBeStatic
    def _add_issue_id_attribute(self, item, marks):
        """Add marks with issue id.

        :param item: pytest test item
        """
        for mark in marks:
            issue_ids = mark.kwargs.get("issue_id", [])
            if not isinstance(issue_ids, list):
                issue_ids = [issue_ids]
            for issue_id in issue_ids:
                item.add_marker(pytest.mark.issue(issue_id))

    # noinspection PyMethodMayBeStatic
    def _get_issue_description_line(self, mark, default_url):
        issue_ids = mark.kwargs.get("issue_id", [])
        if not isinstance(issue_ids, list):
            issue_ids = [issue_ids]
        if not issue_ids:
            return mark.kwargs["reason"]

        mark_url = mark.kwargs.get("url", None) or default_url
        reason = mark.kwargs.get("reason", mark.name)
        issues = ""
        for issue_id in issue_ids:
            issue_url = mark_url.format(issue_id=issue_id) if \
                mark_url else None
            template = " [{issue_id}]({url})" if issue_url \
                else " {issue_id}"
            issues += template.format(issue_id=issue_id,
                                      url=issue_url)
        return "{}:{}".format(reason, issues)

    def _get_issue_info(self, item, marks):
        """Add issues description and issue_type to the test item.

        :param item: pytest test item
        :param marks: pytest marks list
        """
        default_url = item.session.config.getini('rp_issue_system_url')
        issue_short_name = None
        issue_description = ""
        for mark in marks:
            issue_description_line = \
                self._get_issue_description_line(mark, default_url)
            if issue_description_line:
                issue_description += \
                    ("\n* " if issue_description else "* ") + \
                    issue_description_line

            # Set issue_type only for first issue mark
            if "issue_type" in mark.kwargs and issue_short_name is None:
                issue_short_name = mark.kwargs["issue_type"]

        # default value
        issue_short_name = "TI" if issue_short_name is None else \
            issue_short_name

        registered_issues = getattr(self.py_test_service, 'issue_types', {})
        if issue_short_name in registered_issues:
            return Issue(registered_issues[issue_short_name],
                         issue_description)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        """
        Adding issues id marks to the test item.

        :param item:  Pytest.Item
        :return: generator object
        """
        issue_marks = self._process_issue_marks(item)
        if item.session.config.getini('rp_issue_id_marks'):
            self._add_issue_id_attribute(item, issue_marks)

        self.issues[item] = self._get_issue_info(item, issue_marks)

        self.py_test_service.start_pytest_item(item)
        with patching_logger_class():
            with _pytest.logging.catching_logs(self._log_handler,
                                               level=self._log_level):
                yield
        # Finishing item in RP
        self.py_test_service.finish_pytest_item(
            item, self.results[item] or 'SKIPPED', self.issues[item])

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item):
        """
         Change runtest_makereport function.

        :param item: pytest.Item
        :return: None
        """
        report = (yield).get_result()

        if report.longrepr:
            self.py_test_service.post_log(
                escape(report.longreprtext, False),
                loglevel='ERROR')

        # Defining test result
        if report.when == 'setup':
            self.results[item] = 'PASSED'

        if report.failed:
            self.results[item] = 'FAILED'
            return

        if report.skipped:
            if self.results[item] in (None, 'PASSED'):
                self.results[item] = 'SKIPPED'
                if not self.py_test_service.rp.is_skipped_an_issue:
                    self.issues[item] = NOT_ISSUE

        if report.when == 'teardown':
            if self.results[item] == 'PASSED':
                self.issues[item] = None  # Do not report issue if passed
