# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import logging

from .service import PyTestService
from .listener import RPReportListener


def pytest_sessionstart(session):
    PyTestService.init_service(
        project=session.config.getini('rp_project'),
        endpoint=session.config.getini('rp_endpoint'),
        uuid=session.config.getini('rp_uuid'),
        log_batch_size=int(session.config.getini('rp_log_batch_size')),
        ignore_errors=bool(session.config.getini('rp_ignore_errors')),
        ignored_tags=session.config.getini('rp_ignore_tags'),
    )

    PyTestService.start_launch(
        session.config.option.rp_launch,
        tags=session.config.getini('rp_launch_tags'),
        description=session.config.getini('rp_launch_description'),
    )


def pytest_sessionfinish():
    # FixMe: currently method of RP api takes the string parameter
    # so it is hardcoded
    PyTestService.finish_launch(status='RP_Launch')


def pytest_configure(config):
    if not config.option.rp_launch:
        config.option.rp_launch = config.getini('rp_launch')

    # set Pytest_Reporter and configure it
    config._reporter = RPReportListener()

    if hasattr(config, '_reporter'):
        config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    PyTestService.terminate_service()

    if hasattr(config, '_reporter'):
        reporter = config._reporter
        del config._reporter
        config.pluginmanager.unregister(reporter)
        logging.debug('RP is unconfigured')


def pytest_addoption(parser):
    group = parser.getgroup('reporting')
    group.addoption(
        '--rp-launch',
        action='store',
        dest='rp_launch',
        help='Launch name (overrides rp_launch config option)')

    parser.addini(
        'rp_uuid',
        help='UUID')

    parser.addini(
        'rp_endpoint',
        help='Server endpoint')

    parser.addini(
        'rp_project',
        help='Project name')

    parser.addini(
        'rp_launch',
        default='Pytest Launch',
        help='Launch name')

    parser.addini(
        'rp_launch_tags',
        type='args',
        help='Launch tags, i.e Performance Regression')

    parser.addini(
        'rp_launch_description',
        default='',
        help='Launch description')

    parser.addini(
        'rp_log_batch_size',
        default='20',
        help='Size of batch log requests in async mode')

    parser.addini(
        'rp_ignore_errors',
        default=False,
        type='bool',
        help='Ignore Report Portal errors (exit otherwise)')

    parser.addini(
        'rp_ignore_tags',
        type='args',
        help='Ignore specified pytest markers, i.e parametrize')
