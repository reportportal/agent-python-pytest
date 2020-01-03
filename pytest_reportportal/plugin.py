# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import logging
import dill as pickle
import pytest
import requests
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
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    if is_master(session.config):
        session.config.py_test_service.init_service(
            project=session.config.getini('rp_project'),
            endpoint=session.config.getini('rp_endpoint'),
            uuid=session.config.getini('rp_uuid'),
            log_batch_size=int(session.config.getini('rp_log_batch_size')),
            ignore_errors=bool(session.config.getini('rp_ignore_errors')),
            ignored_tags=session.config.getini('rp_ignore_tags'),
            verify_ssl=session.config.getini('rp_verify_ssl'),
            retries=int(session.config.getini('retries')),
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
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    session.config.py_test_service.collect_tests(session)


def wait_launch(rp_client):
    timeout = time.time() + LAUNCH_WAIT_TIMEOUT
    while not rp_client.launch_id:
        if time.time() > timeout:
            raise Exception("Launch not found")
        time.sleep(1)


def pytest_sessionfinish(session):
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    shouldfail = getattr(session, 'shouldfail', False)
    nowait = True if shouldfail else False

    if is_master(session.config):
        session.config.py_test_service.finish_launch(
            status='RP_Launch', force=nowait)

    session.config.py_test_service.terminate_service(nowait=nowait)


def pytest_configure(config):

    if config.getoption('--collect-only', default=False) or \
            config.getoption('--setup-plan', default=False) or \
            not config.option.rp_enabled:
        config._reportportal_configured = False
        return

    project = config.getini('rp_project')
    endpoint = config.getini('rp_endpoint')
    uuid = config.getini('rp_uuid')
    ignore_errors = config.getini('rp_ignore_errors')
    config._reportportal_configured = all([project, endpoint, uuid])

    if config._reportportal_configured and ignore_errors:
        try:
            verify_ssl = config.getini('rp_verify_ssl')
            r = requests.get(
                '{0}/api/v1/project/{1}'.format(endpoint, project),
                headers={
                    'Authorization': 'bearer {0}'.format(uuid)
                },
                verify=verify_ssl
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as exc:
            log.exception(exc)
            config._reportportal_configured = False

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
        dest='rp_enabled',
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

    parser.addini(
        'rp_issue_marks',
        type='args',
        default='',
        help='Pytest marks to get issue information')

    parser.addini(
        'rp_issue_system_url',
        default='',
        help='URL to get issue description. Issue id from pytest mark will be added to this URL')

    parser.addini(
        'rp_verify_ssl',
        default=True,
        type='bool',
        help='Verify HTTPS calls')

    parser.addini(
        'rp_display_suite_test_file',
        default=True,
        type='bool',
        help="In case of True, include the suite's relative file path in the launch name as a convention of "
             "'<RELATIVE_FILE_PATH>::<SUITE_NAME>'. In case of False, set the launch name to be the suite name "
             "only - this flag is relevant only when 'rp_hierarchy_module' flag is set to False")

    parser.addini(
        'rp_issue_id_marks',
        type='bool',
        default=True,
        help='Adding tag with issue id to the test')

    parser.addini(
        'retries',
        default='0',
        help='Amount of retries for performing REST calls to RP server')
