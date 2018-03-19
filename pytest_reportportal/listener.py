import cgi
import pytest
import logging


try:
    # This try/except can go away once we support pytest >= 3.3
    import _pytest.logging
    PYTEST_HAS_LOGGING_PLUGIN = True
    from .rp_logging import RPLogHandler, patching_logger_class
except ImportError:
    PYTEST_HAS_LOGGING_PLUGIN = False


class RPReportListener(object):
    def __init__(self, py_test_service, log_level=logging.NOTSET):
        # Test Item result
        self.PyTestService = py_test_service
        self.result = None
        self._log_level = log_level
        if PYTEST_HAS_LOGGING_PLUGIN:
            self._log_handler = RPLogHandler(log_level, filter_reportportal_client_logs=True)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        self.PyTestService.start_pytest_item(item)
        if PYTEST_HAS_LOGGING_PLUGIN:
            # This check can go away once we support pytest >= 3.3
            with patching_logger_class():
                with _pytest.logging.catching_logs(self._log_handler,
                                                   level=self._log_level):
                    yield
        else:
            yield
        self.PyTestService.finish_pytest_item(self.result or 'SKIPPED')

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self):
        report = (yield).get_result()

        if report.longrepr:
            self.PyTestService.post_log(
                # Used for support python 2.7
                cgi.escape(report.longreprtext),
                loglevel='ERROR',
            )

        if report.when == 'setup':
            self.result = None
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
