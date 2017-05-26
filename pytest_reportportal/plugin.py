# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import logging
import cgi

import pytest

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

        if report.longrepr:
            PyTestService.post_log(
                cgi.escape(report.longreprtext),
                loglevel='ERROR',
            )

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
    PyTestService.init_service(
        project=session.config.getini("rp_project"),
        endpoint=session.config.getini("rp_endpoint"),
        uuid=session.config.getini("rp_uuid"),
        log_batch_size=int(session.config.getini("rp_log_batch_size"))
    )

    PyTestService.start_launch(
        session.config.option.rp_launch,
        tags=session.config.getini("rp_launch_tags"),
        description=session.config.getini("rp_launch_description"),
    )


def pytest_sessionfinish(session):
    # FixMe: currently method of RP api takes the string parameter
    # so it is hardcoded
    PyTestService.finish_launch(status="RP_Launch")


def pytest_configure(config):
    if not config.option.rp_launch:
        config.option.rp_launch = config.getini("rp_launch")

    # set Pytest_Reporter and configure it
    config._reporter = RP_Report_Listener()

    if hasattr(config, "_reporter"):
        config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    PyTestService.terminate_service()

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
        help="Launch name (overrides rp_launch config option)")

    parser.addini(
        "rp_uuid",
        help="UUID")

    parser.addini(
        "rp_endpoint",
        help="Server endpoint")

    parser.addini(
        "rp_project",
        help="Project name")

    parser.addini(
        "rp_launch",
        default="Pytest Launch",
        help="Launch name")

    parser.addini(
        "rp_launch_tags",
        type="args",
        help="Launch tags, i.e Performance Regression")

    parser.addini(
        "rp_launch_description",
        default="",
        help="Launch description")

    parser.addini(
        "rp_log_batch_size",
        default="20",
        help="Size of batch log requests in async mode")
