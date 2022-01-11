"""RPReportListener implements Pytest hooks required for item reporting."""

import logging

import pytest

try:
    from html import escape  # python3
except ImportError:
    from cgi import escape  # python2

import _pytest.logging
from .rp_logging import RPLogHandler, patching_logger_class


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
        self.result = None
        self.issue = {}
        self._log_level = log_level
        self._log_handler = \
            RPLogHandler(py_test_service=py_test_service,
                         level=log_level,
                         filter_client_logs=True,
                         endpoint=endpoint)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        """
        Adding issues id marks to the test item.

        :param item:  Pytest.Item
        :return: generator object
        """
        self._add_issue_id_marks(item)
        item_id = self.py_test_service.start_pytest_item(item)
        with patching_logger_class():
            with _pytest.logging.catching_logs(self._log_handler,
                                               level=self._log_level):
                yield
        # Finishing item in RP
        self.py_test_service.finish_pytest_item(
            item, item_id, self.result or 'SKIPPED', self.issue or None)
        # Flush log buffer
        self.py_test_service.rp.terminate()

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
            self.result = None
            self.issue = {}

        if report.failed:
            self.result = 'FAILED'
            self._add_issue_info(item, report)
        elif report.skipped:
            if self.result in (None, 'PASSED'):
                self.result = 'SKIPPED'
                if self.py_test_service.rp.is_skipped_an_issue:
                    self._add_issue_info(item, report)
        else:
            if self.result is None:
                self.result = 'PASSED'

    @staticmethod
    def _add_issue_id_marks(item):
        """Add marks with issue id.

        :param item: pytest test item
        """
        issue_marks = item.session.config.getini('rp_issue_marks')
        if item.session.config.getini('rp_issue_id_marks'):
            for mark_name in issue_marks:
                for mark in item.iter_markers(name=mark_name):
                    if mark:
                        issue_ids = mark.kwargs.get("issue_id", [])
                        if not isinstance(issue_ids, list):
                            issue_ids = [issue_ids]
                        for issue_id in issue_ids:
                            mark_issue = "{}:{}".format(mark.name, issue_id)
                            try:
                                # register mark in pytest
                                pytest.mark._markers.add(mark_issue),
                                # for pytest >= 4.5.0
                            except AttributeError:
                                pass
                            item.add_marker(mark_issue)

    def _add_issue_info(self, item, report):
        """Add issues description and issue_type to the test item.

        ToDo: THIS NEEDS TO BE REWRITTEN. LOOKS UGLY.
        :param item: pytest test item
        :param report: pytest report instance
        """
        url = item.session.config.getini('rp_issue_system_url')
        issue_marks = item.session.config.getini('rp_issue_marks')
        issue_type = None
        comment = ""

        for mark_name in issue_marks:
            for mark in item.iter_markers(name=mark_name):
                if not mark:
                    continue

                mark_comment = ""
                mark_url = mark.kwargs.get("url", None) or url
                issue_ids = mark.kwargs.get("issue_id", [])
                if not isinstance(issue_ids, list):
                    issue_ids = [issue_ids]

                if issue_ids:
                    mark_comment = mark.kwargs.get("reason", mark.name)
                    mark_comment += ":"
                    for issue_id in issue_ids:
                        issue_url = mark_url.format(issue_id=issue_id) if \
                            mark_url else None
                        template = " [{issue_id}]({url})" if issue_url \
                            else " {issue_id}"
                        mark_comment += template.format(issue_id=issue_id,
                                                        url=issue_url)
                elif "reason" in mark.kwargs:
                    mark_comment = mark.kwargs["reason"]

                if mark_comment:
                    comment += ("\n* " if comment else "* ") + mark_comment

                # Set issue_type only for first issue mark
                if "issue_type" in mark.kwargs and issue_type is None:
                    issue_type = mark.kwargs["issue_type"]

        # default value
        issue_type = "TI" if issue_type is None else issue_type

        if issue_type and issue_type in getattr(
                self.py_test_service, 'issue_types', ()):
            if comment:
                self.issue['comment'] = comment
            self.issue['issueType'] = \
                self.py_test_service.issue_types[issue_type]
            # self.issue['ignoreAnalyzer'] = True ???
        elif (report.when == 'setup') and report.skipped:
            self.issue['issueType'] = 'NOT_ISSUE'
