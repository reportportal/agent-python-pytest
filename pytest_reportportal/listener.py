import pytest
import logging
try:
    from html import escape   # python3
except ImportError:
    from cgi import escape    # python2


try:
    # This try/except can go away once we support pytest >= 3.3
    import _pytest.logging
    PYTEST_HAS_LOGGING_PLUGIN = True
    from .rp_logging import RPLogHandler, patching_logger_class
except ImportError:
    PYTEST_HAS_LOGGING_PLUGIN = False


class RPReportListener(object):
    def __init__(self, py_test_service,
                 log_level=logging.NOTSET,
                 endpoint=None):
        # Test Item result
        self.PyTestService = py_test_service
        self.result = None
        self.issue = {}
        self._log_level = log_level
        if PYTEST_HAS_LOGGING_PLUGIN:
            self._log_handler = RPLogHandler(py_test_service=py_test_service,
                                             level=log_level,
                                             filter_reportportal_client_logs=True,
                                             endpoint=endpoint)

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
        self.PyTestService.finish_pytest_item(item, self.result or 'SKIPPED', self.issue or None)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item):
        report = (yield).get_result()

        if report.longrepr:
            self.PyTestService.post_log(
                escape(report.longreprtext, False),
                loglevel='ERROR',
            )

        if report.when == 'setup':
            self.result = None
            self.issue = {}
            if report.failed:
                # This happens for example when a fixture fails to run
                # causing the test to error
                self.result = 'FAILED'
                self._add_issue_info(item, report)
            elif report.skipped:
                # This happens when a testcase is marked "skip".  It will
                # show in reportportal as not requiring investigation.
                self.result = 'SKIPPED'
                self._add_issue_info(item, report)

        if report.when == 'call':
            if report.passed:
                item_result = 'PASSED'
            elif report.skipped:
                item_result = 'SKIPPED'
                self._add_issue_info(item, report)
            else:
                item_result = 'FAILED'
                self._add_issue_info(item, report)
            self.result = item_result


    def _add_issue_info(self, item, report):

        issue_type = None
        comment = ""
        url = item.session.config.getini('rp_issue_system_url')
        issue_marks = item.session.config.getini('rp_issue_marks')

        for mark_name in issue_marks:
            try:
                mark = item.get_closest_marker(mark_name)
            except AttributeError:
                # pytest < 3.6
                mark = item.get_marker(mark_name)

            if mark:
                if "reason" in mark.kwargs:
                    comment += "\n" if comment else ""
                    comment += mark.kwargs["reason"]
                if "issue_id" in mark.kwargs:
                    issue_ids = mark.kwargs["issue_id"]
                    if not isinstance(issue_ids, list):
                        issue_ids = [issue_ids]
                    comment += "\n" if comment else ""
                    comment += "Issues:"
                    for issue_id in issue_ids:
                        template = (" [{issue_id}]" + "({})".format(url)) if url else " {issue_id}"
                        comment += template.format(issue_id=issue_id)

                if "issue_type" in mark.kwargs:
                    issue_type = mark.kwargs["issue_type"]

        issue_type = "TI" if issue_type is None else issue_type

        if issue_type and self.PyTestService.issue_types \
                and (issue_type in self.PyTestService.issue_types):
            if comment:
                self.issue['comment'] = comment
            self.issue['issue_type'] = self.PyTestService.issue_types[issue_type]
            # self.issue['ignoreAnalyzer'] = True ???
        elif (report.when == 'setup') and report.skipped:
            self.issue['issue_type'] = 'NOT_ISSUE'
