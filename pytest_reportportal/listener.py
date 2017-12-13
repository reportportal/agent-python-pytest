import cgi
import pytest

from .service import PyTestService


class RPReportListener(object):
    def __init__(self):
        # Test Item result
        self.result = None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        PyTestService.start_pytest_item(item)
        yield
        PyTestService.finish_pytest_item(self.result or 'SKIPPED')

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self):
        report = (yield).get_result()

        if report.longrepr:
            PyTestService.post_log(
                # Used for support python 2.7
                cgi.escape(report.longreprtext),
                loglevel='ERROR',
            )

        if report.when == 'setup':
            if report.failed:
                # This happens for example when a fixture fails to run
                # causing the test to error
                self.result = 'FAILED'

        if report.when == 'call':
            if report.passed:
                item_result = 'PASSED'
            elif report.skipped:
                item_result = 'SKIPPED'
            else:
                item_result = 'FAILED'
            self.result = item_result
