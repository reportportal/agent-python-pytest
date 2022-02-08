"""This module contains changed pytest for report-portal."""

# This program is free software: you can redistribute it
# and/or modify it under the terms of the GPL licence

import dill as pickle
import logging
import time

import pytest
import requests

from pytest_reportportal import LAUNCH_WAIT_TIMEOUT
from reportportal_client.errors import ResponseError

from .config import AgentConfig
from .listener import RPReportListener
from .service import PyTestServiceClass


log = logging.getLogger(__name__)


def check_connection(agent_config, pytest_config):
    """Check connection to RP using provided options.

    If connection is not successful, then we update _reportportal_configured
    attribute of the Config object to False.
    :param agent_config:  Instance of the AgentConfig class
    :param pytest_config: config object of PyTest
    """
    if pytest_config._reportportal_configured and \
            not agent_config.rp_skip_connection_test:
        url = '{0}/api/v1/project/{1}'.format(agent_config.rp_endpoint,
                                              agent_config.rp_project)
        headers = {'Authorization': 'bearer {0}'.format(agent_config.rp_uuid)}
        try:
            resp = requests.get(url, headers=headers,
                                verify=agent_config.rp_verify_ssl)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            log.exception(exc)
            log.error("Unable to connect to Report Portal, the launch won't be"
                      " reported")
            pytest_config._reportportal_configured = False


def is_master(config):
    """Validate workerinput attribute of the Config object.

    True if the code, running the given pytest.config object,
    is running as the xdist master node or not running xdist at all.
    """
    return not hasattr(config, 'workerinput')


def wait_launch(rp_client):
    """Wait for the launch startup.

    :param rp_client: Instance of the ReportPortalService class
    """
    timeout = time.time() + LAUNCH_WAIT_TIMEOUT
    while not rp_client.launch_id:
        if time.time() > timeout:
            raise Exception("Launch has not started.")
        time.sleep(1)


@pytest.mark.optionalhook
def pytest_configure_node(node):
    """Configure xdist node controller.

    :param node: Object of the xdist WorkerController class
    """
    if node.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return
    node.workerinput['py_test_service'] = pickle.dumps(
        node.config.py_test_service)


def pytest_sessionstart(session):
    """Start test session.

    :param session: Object of the pytest Session class
    """
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return
    if is_master(session.config):
        config = session.config
        try:
            config.py_test_service.init_service()
        except ResponseError as response_error:
            log.warning('Failed to initialize reportportal-client service. '
                        'Reporting is disabled.')
            log.debug(str(response_error))
            config.py_test_service.rp = None
            return
        if not config._reporter_config.rp_launch_id:
            config.py_test_service.start_launch()
            if config.pluginmanager.hasplugin('xdist'):
                wait_launch(session.config.py_test_service.rp)


def pytest_collection_finish(session):
    """Collect tests if session is configured.

    :param session: Object of the pytest Session class
    """
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return

    session.config.py_test_service.collect_tests(session)


def pytest_sessionfinish(session):
    """Finish current test session.

    :param session: Object of the pytest Session class
    """
    if session.config._reportportal_configured is False:
        # Stop now if the plugin is not properly configured
        return
    session.config.py_test_service.finish_suites()
    if is_master(session.config):
        if not session.config.option.rp_launch_id:
            session.config.py_test_service.finish_launch()
    rp = session.config.py_test_service.rp
    # TODO: fix logging
    if rp:
        rp.terminate()


def register_markers(config):
    """Register plugin's markers, to avoid declaring them in `pytest.ini`.

    :param config: Object of the pytest Config class
    """
    config.addinivalue_line(
        "markers", "issue(issue_id, reason, issue_type, url): mark test with "
                   "information about skipped or failed result"
    )


def pytest_configure(config):
    """Update Config object with attributes required for reporting to RP.

    :param config: Object of the pytest Config class
    """
    register_markers(config)

    skip = (config.getoption('--collect-only', default=False) or
            config.getoption('--setup-plan', default=False) or
            not config.option.rp_enabled)
    if skip:
        config._reportportal_configured = False
        return

    agent_config = AgentConfig(config)
    cond = (agent_config.rp_project, agent_config.rp_endpoint,
            agent_config.rp_uuid)
    config._reportportal_configured = all(cond)
    if config._reportportal_configured is False:
        log.debug('One of the following parameters is unset: rp_project:{}, '
                  'rp_endpoint:{}, rp_uuid:{}!'.format(*cond))
        log.debug('Disabling reporting to RP.')
        return

    check_connection(agent_config, config)
    if config._reportportal_configured is False:
        log.debug('Failed to establish connection with RP. '
                  'Disabling reporting.')
        return

    config._reporter_config = agent_config

    if is_master(config):
        config.py_test_service = PyTestServiceClass(agent_config)
    else:
        config.py_test_service = pickle.loads(
            config.workerinput['py_test_service'])

    config._reporter = RPReportListener(
        config.py_test_service,
        log_level=agent_config.rp_log_level or logging.NOTSET,
        endpoint=agent_config.rp_endpoint)
    if hasattr(config, '_reporter'):
        config.pluginmanager.register(config._reporter)


def pytest_unconfigure(config):
    """Clear config from reporter.

    :param config: Object of the pytest Config class
    """
    if getattr(config, '_reportportal_configured', False) is False:
        # Stop now if the plugin is not properly configured
        return
    if hasattr(config, '_reporter'):
        reporter = config._reporter
        del config._reporter
        config.pluginmanager.unregister(reporter)
        log.debug('RP is unconfigured.')


def pytest_addoption(parser):
    """Add support for the RP-related options.

    :param parser: Object of the Parser class
    """
    group = parser.getgroup('reporting')

    def add_shared_option(name, help, default=None, action='store'):
        """
        Add an option to both the command line and the .ini file.

        This function modifies `parser` and `group` from the outer scope.

        :param name:     name of the option
        :param help:     help message
        :param default:  default value
        :param action:   `group.addoption` action
        """
        parser.addini(
            name=name,
            default=default,
            help=help,
        )
        group.addoption(
            '--{0}'.format(name.replace('_', '-')),
            action=action,
            dest=name,
            help='{help} (overrides {name} config option)'.format(
                help=help,
                name=name,
            ),
        )

    group.addoption(
        '--reportportal',
        action='store_true',
        dest='rp_enabled',
        default=False,
        help='Enable ReportPortal plugin'
    )
    add_shared_option(
        name='rp_launch',
        help='Launch name',
        default='Pytest Launch',
    )
    add_shared_option(
        name='rp_launch_id',
        help='Use already existing launch-id. The plugin won\'t control the '
             'Launch status',
    )
    add_shared_option(
        name='rp_launch_description',
        help='Launch description',
        default='',
    )
    add_shared_option(name='rp_project', help='Project name')
    add_shared_option(
        name='rp_log_level',
        help='Logging level for automated log records reporting',
    )
    add_shared_option(
        name='rp_rerun',
        help='Marks the launch as a rerun',
        default=False,
        action='store_true',
    )
    add_shared_option(
        name='rp_rerun_of',
        help='ID of the launch to be marked as a rerun (use only with '
             'rp_rerun=True)',
        default='',
    )
    add_shared_option(
        name='rp_parent_item_id',
        help='Create all test item as child items of the given (already '
             'existing) item.',
    )
    add_shared_option(name='rp_uuid', help='UUID')
    add_shared_option(name='rp_endpoint', help='Server endpoint')
    add_shared_option(
        name='rp_mode',
        help='Visibility of current launch [DEFAULT, DEBUG]',
        default='DEFAULT'
    )

    parser.addini(
        'rp_launch_attributes',
        type='args',
        help='Launch attributes, i.e Performance Regression')
    parser.addini(
        'rp_tests_attributes',
        type='args',
        help='Attributes for all tests items, e.g. Smoke')
    parser.addini(
        'rp_log_batch_size',
        default='20',
        help='Size of batch log requests in async mode')
    parser.addini(
        'rp_ignore_attributes',
        type='args',
        help='Ignore specified pytest markers, i.e parametrize')
    parser.addini(
        'rp_is_skipped_an_issue',
        default=True,
        type='bool',
        help='Treat skipped tests as required investigation')
    parser.addini(
        'rp_hierarchy_dirs_level',
        default='0',
        help='Directory starting hierarchy level')
    parser.addini(
        'rp_issue_system_url',
        default='',
        help='URL to get issue description. Issue id '
             'from pytest mark will be added to this URL')
    parser.addini(
        'rp_verify_ssl',
        default=True,
        type='bool',
        help='Verify HTTPS calls')
    parser.addini(
        'rp_issue_id_marks',
        type='bool',
        default=True,
        help='Add tag with issue id to the test')
    parser.addini(
        'retries',
        default='0',
        help='Amount of retries for performing REST calls to RP server')
    parser.addini(
        'rp_skip_connection_test',
        default=False,
        type='bool',
        help='Skip Report Portal connection test')
