import pytest
# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence
import logging
from .service import PyTestService


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
            # test item session will be started in RP
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
            self.called = None


def pytest_sessionstart(session):
    config = session.config
    if config.option.rp_launch:
        # get config parameters if rp_launch option is set
        rp_uuid = config.getini("rp_uuid")
        rp_project = config.getini("rp_project")
        rp_endpoint = config.getini("rp_endpoint")
        rp_launch_tags = config.getini("rp_launch_tags")
        # initialize PyTest
        PyTestService.init_service(
                project=rp_project,
                endpoint=rp_endpoint,
                uuid=rp_uuid)
        launch_name = config.getoption("rp_launch")

        PyTestService.start_launch(launch_name, tags=rp_launch_tags)


def pytest_sessionfinish(session):
    config = session.config
    if config.option.rp_launch:
        # FixMe: currently method of RP api takes the string parameter
        # so it is hardcoded
        PyTestService.finish_launch(status="RP_Launch")


def pytest_configure(config):
    rp_launch = config.getoption("rp_launch")
    if rp_launch:
        # set Pytest_Reporter and configure it
        config._reporter = RP_Report_Listener()

        if hasattr(config, "_reporter"):
            config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    if hasattr(config, "_reporter"):
        reporter = config._reporter
        del config._reporter
        config.pluginmanager.unregister(reporter)
        logging.debug("RP is unconfigured")


def pytest_addoption(parser):
    group = parser.getgroup("reporting")
    group.addoption(
        "--rp-launch",
        action="store",
        dest="rp_launch",
        help="The Launch name for RP")

    parser.addini(
        "rp_uuid",
        help="Uid of RP user")

    parser.addini(
        "rp_endpoint",
        help="RP server")

    parser.addini(
        "rp_project",
        help="RP Project")

    parser.addini(
        "rp_launch_tags",
        type="args",
        help="Tags for of RP Launch, i.e Perfomance Regression")
