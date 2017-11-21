import cgi
import pytest

from .service import PyTestService


class RPReportListener(object):
    def __init__(self):
        # Identifier if TestItem is called:
        # if setup is failed, pytest will NOT call
        # TestItem and Result will not reported!
        self.called = False

        # Test Item result
        self.result = None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        PyTestService.start_pytest_item(item)
        yield
        item_result = self.result if self.called else 'SKIPPED'
        PyTestService.finish_pytest_item(item_result)
        self.called = False

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self):
        report = (yield).get_result()

        if report.longrepr:
            PyTestService.post_log(
                # Used for support python 2.7
                cgi.escape(report.longreprtext),
                loglevel='ERROR',
            )

        if report.when == 'call':
            self.called = True

            if report.passed:
                item_result = 'PASSED'
            elif report.failed:
                item_result = 'FAILED'
            else:
                item_result = 'SKIPPED'

            self.result = item_result
