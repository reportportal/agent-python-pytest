# This program is free software: you can redistribute it and/or modify iit under the terms of the GPL licence
import pytest
import logging
from service import PyTestService


class RP_Report_Listener(object):

    # Identifier if TestItem is called:
    # if setup is failed, pytest will NOT call
    #  TestItem and Result will not reported!
    called = None
    # Test Item result
    result = None

    @pytest.mark.hookwrapper
    def pytest_runtest_makereport(self, item, call):
        report = (yield).get_result()
        if report.when == "setup":
            # when function pytest_setup is called,
            # test item session is started in RP
            PyTestService.start_pytest_item(item)

        if report.when == "call":
            self.called = True
            if report.passed:
                item_result = "PASSED"
            elif report.failed:
                item_result = "FAILED"
            else:
                item_result = "SKIPPED"

            self.result = item_result

        if report.when == "teardown":
            # If item is called, result of TestItem is reported
            if self.called is True:
                item_result = self.result
            else:
                # If setup - failed or skipped,
                # the TestItem will reported as SKIPPED
                item_result = "SKIPPED"
            PyTestService.finish_pytest_item(item_result)


def pytest_sessionstart(session):
    config = session.config
    if config.option.rp_launch:
        # get config parameters if rp_launch option is set
        rp_uuid = config.getini('rp_uuid')
        rp_project = config.getini('rp_project')
        rp_endpoint = config.getini('rp_endpoint')
        # initialize PyTest
        PyTestService.init_service(
                project=rp_project,
                endpoint=rp_endpoint,
                uuid=rp_uuid)
        launch_name = config.getoption('rp_launch')

        PyTestService.start_launch(launch_name)


def pytest_sessionfinish(session):
    config = session.config
    if config.option.rp_launch:
        PyTestService.finish_launch("RP_Launch")


def pytest_configure(config):
    rp_launch = config.getoption('rp_launch')
    if rp_launch:
        # set Pytest_Reporter and configure it
        config._reporter = RP_Report_Listener()

        if hasattr(config, '_reporter'):
            config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    if hasattr(config, '_reporter'):
        reporter = config._reporter
        del config._reporter
        config.pluginmanager.unregister(reporter)
        logging.debug('ReportPortal is unconfigured')


def pytest_addoption(parser):
    group = parser.getgroup("reporting")
    group.addoption(
        '--rp_launch',
        action='store',
        dest=None,
        help="The Launch name for ReportPortal, i.e PyTest")

    parser.addini(
        'rp_uuid',
        help="Uid of RP user")

    parser.addini(
        'rp_endpoint',
        help="Report portal server")

    parser.addini(
        "rp_project",
        help='Report Portal Project')
