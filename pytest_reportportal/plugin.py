# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import logging
import dill as pickle
import pytest
import time
from .service import PyTestServiceClass
from .listener import RPReportListener


def is_master(config):
    """
    True if the code running the given pytest.config object is running in a xdist master
    node or not running xdist at all.
    """
    return not hasattr(config, 'slaveinput')


@pytest.mark.optionalhook
def pytest_configure_node(node):
    node.slaveinput['py_test_service'] = pickle.dumps(node.config.py_test_service)


def pytest_sessionstart(session):
    if session.config.getoption('--collect-only', default=False) is True:
        return
    if is_master(session.config):
        session.config.py_test_service.init_service(
            project=session.config.getini('rp_project'),
            endpoint=session.config.getini('rp_endpoint'),
            uuid=session.config.getini('rp_uuid'),
            log_batch_size=int(session.config.getini('rp_log_batch_size')),
            ignore_errors=bool(session.config.getini('rp_ignore_errors')),
            ignored_tags=session.config.getini('rp_ignore_tags'),
        )

        session.config.py_test_service.start_launch(
            session.config.option.rp_launch,
            tags=session.config.getini('rp_launch_tags'),
            description=session.config.getini('rp_launch_description'),
        )
        if session.config.pluginmanager.hasplugin('xdist'):
            wait_launch(session.config.py_test_service.RP.rp_client.launch_id)


def wait_launch(self):
    timeout = time.time() + 10
    while not self.rp_client.launch_id:
        if time.time() > timeout:
            raise Exception("Launch not found")
        time.sleep(1)


def pytest_sessionfinish(session):
    if session.config.getoption('--collect-only', default=False) is True:
        return

    # FixMe: currently method of RP api takes the string parameter
    # so it is hardcoded
    if is_master(session.config):
        session.config.py_test_service.finish_launch(status='RP_Launch')


def pytest_configure(config):
    if not config.option.rp_launch:
        config.option.rp_launch = config.getini('rp_launch')

    if is_master(config):
        config.py_test_service = PyTestServiceClass()
    else:
        config.py_test_service = pickle.loads(config.slaveinput['py_test_service'])
        config.py_test_service.RP.listener.start()

    # set Pytest_Reporter and configure it
    config._reporter = RPReportListener(config.py_test_service)
    if hasattr(config, '_reporter'):
        config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    config.py_test_service.terminate_service()

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