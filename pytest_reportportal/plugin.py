# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import logging
import dill as pickle
import pytest
import time
from pytest_reportportal import LAUNCH_WAIT_TIMEOUT
from .service import PyTestServiceClass
from .listener import RPReportListener

try:
    # This try/except can go away once we support pytest >= 3.3
    import _pytest.logging
    PYTEST_HAS_LOGGING_PLUGIN = True
except ImportError:
    PYTEST_HAS_LOGGING_PLUGIN = False

log = logging.getLogger(__name__)


def is_master(config):
    """
    True if the code running the given pytest.config object is running in a xdist master
    node or not running xdist at all.
    """
    return not hasattr(config, 'slaveinput')


@pytest.mark.optionalhook
def pytest_configure_node(node):
    if node.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return
    node.slaveinput['py_test_service'] = pickle.dumps(node.config.py_test_service)


def pytest_sessionstart(session):
    if session.config.getoption('--collect-only', default=False) is True:
        return

    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    if not session.config.option.enabled:
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
            description=session.config.option.rp_launch_description
        )
        if session.config.pluginmanager.hasplugin('xdist'):
            wait_launch(session.config.py_test_service.RP.rp_client)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    # Items need to be sorted so that we can hierarchically report
    # * test-filename:
    #   * Test Suite:
    #     * Test case
    #
    # Hopefully sorting by fspath and parnt name will allow proper
    # order between test modules and any test classes.
    # We don't sort by nodeid because that changes the order of
    # parametrized tests which can rely on that order
    items.sort(key=lambda f: (f.fspath, f.parent.name))


def pytest_collection_finish(session):
    if session.config.getoption('--collect-only', default=False) is True:
        return

    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    if is_master(session.config):
        session.config.py_test_service.collect_tests(session)


def wait_launch(rp_client):
    timeout = time.time() + LAUNCH_WAIT_TIMEOUT
    while not rp_client.launch_id:
        if time.time() > timeout:
            raise Exception("Launch not found")
        time.sleep(1)


def pytest_sessionfinish(session):
    if session.config.getoption('--collect-only', default=False) is True:
        return

    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    if not session.config.option.enabled:
        return

    # FixMe: currently method of RP api takes the string parameter
    # so it is hardcoded
    if is_master(session.config):
        session.config.py_test_service.finish_launch(status='RP_Launch')

    session.config.py_test_service.terminate_service()


def pytest_configure(config):
    project = config.getini('rp_project')
    endpoint = config.getini('rp_endpoint')
    uuid = config.getini('rp_uuid')
    config._reportportal_configured = all([project, endpoint, uuid])
    if config._reportportal_configured is False:
        return

    if not config.option.rp_launch:
        config.option.rp_launch = config.getini('rp_launch')
    if not config.option.rp_launch_description:
        config.option.rp_launch_description = config.getini('rp_launch_description')

    if is_master(config):
        config.py_test_service = PyTestServiceClass()
    else:
        config.py_test_service = pickle.loads(config.slaveinput['py_test_service'])
        config.py_test_service.RP.listener.start()

    # set Pytest_Reporter and configure it
    if PYTEST_HAS_LOGGING_PLUGIN:
        # This check can go away once we support pytest >= 3.3
        log_level = _pytest.logging.get_actual_log_level(config, 'rp_log_level')
        if log_level is None:
            log_level = logging.NOTSET
    else:
        log_level = logging.NOTSET

    config._reporter = RPReportListener(config.py_test_service,
                                        log_level=log_level,
                                        endpoint=endpoint)

    if hasattr(config, '_reporter'):
        config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    if config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    if hasattr(config, '_reporter'):
        reporter = config._reporter
        del config._reporter
        config.pluginmanager.unregister(reporter)
        log.debug('RP is unconfigured')


def pytest_addoption(parser):
    group = parser.getgroup('reporting')
    group.addoption(
        '--rp-launch',
        action='store',
        dest='rp_launch',
        help='Launch name (overrides rp_launch config option)')
    group.addoption(
        '--rp-launch-description',
        action='store',
        dest='rp_launch_description',
        help='Launch description (overrides rp_launch_description config option)')

    group.addoption(
        '--reportportal',
        action='store_true',
        dest='enabled',
        default=False,
        help='Enable ReportPortal plugin'
    )

    if PYTEST_HAS_LOGGING_PLUGIN:
        group.addoption(
            '--rp-log-level',
            dest='rp_log_level',
            default=None,
            help='Logging level for automated log records reporting'
        )
        parser.addini(
            'rp_log_level',
            default=None,
            help='Logging level for automated log records reporting'
        )

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
        'rp_tests_tags',
        type='args',
        help='Tags for all tests items, e.g. Smoke')

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

    parser.addini(
        'rp_hierarchy_dirs_level',
        default=0,
        help='Directory starting hierarchy level')

    parser.addini(
        'rp_hierarchy_dirs',
        default=False,
        type='bool',
        help='Enables hierarchy for directories')

    parser.addini(
        'rp_hierarchy_module',
        default=True,
        type='bool',
        help='Enables hierarchy for module')

    parser.addini(
        'rp_hierarchy_class',
        default=True,
        type='bool',
        help='Enables hierarchy for class')

    parser.addini(
        'rp_hierarchy_parametrize',
        default=False,
        type='bool',
        help='Enables hierarchy for parametrized tests')
