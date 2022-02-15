"""RPReportListener implements Pytest hooks required for item reporting."""

import logging

import pytest

try:
    # noinspection PyCompatibility
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
        self.results = {}
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
        self.py_test_service.start_pytest_item(item)
        with patching_logger_class():
            with _pytest.logging.catching_logs(self._log_handler,
                                               level=self._log_level):
                yield
        # Finishing item in RP
        self.py_test_service.finish_pytest_item(
            item, self.results[item] or 'SKIPPED')

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
