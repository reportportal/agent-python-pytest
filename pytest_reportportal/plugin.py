#  Copyright (c) 2023 https://reportportal.io .
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

"""This module contains changed pytest for ReportPortal."""

import logging
import os.path
import time

import _pytest.logging
import dill as pickle
import pytest
import requests
from reportportal_client import RPLogHandler
from reportportal_client.errors import ResponseError
from reportportal_client.logs import MAX_LOG_BATCH_PAYLOAD_SIZE

from pytest_reportportal import LAUNCH_WAIT_TIMEOUT
from .config import AgentConfig
from .rp_logging import patching_logger_class, patching_thread_class
from .service import PyTestServiceClass

log = logging.getLogger(__name__)

MANDATORY_PARAMETER_MISSED_PATTERN = \
    'One of the following mandatory parameters is unset: ' + \
    'rp_project: {}, ' + \
    'rp_endpoint: {}, ' + \
    'rp_api_key: {}'

FAILED_LAUNCH_WAIT = 'Failed to initialize reportportal-client service. ' \
                     + 'Waiting for Launch start timed out. ' \
                     + 'Reporting is disabled.'


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    """Configure xdist node controller.

    :param node: Object of the xdist WorkerController class
    """
    # noinspection PyProtectedMember
    if not node.config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return
    node.workerinput['py_test_service'] = pickle.dumps(node.config.py_test_service)


def is_control(config):
    """Validate workerinput attribute of the Config object.

    True if the code, running the given pytest.config object,
    is running as the xdist control node or not running xdist at all.
    """
    return not hasattr(config, 'workerinput')


def wait_launch(rp_client):
    """Wait for the launch startup.

    :param rp_client: Instance of the ReportPortalService class
    """
    timeout = time.time() + LAUNCH_WAIT_TIMEOUT
    while not rp_client.launch_id:
        if time.time() > timeout:
            return False
        time.sleep(1)
    return True


# noinspection PyProtectedMember
def pytest_sessionstart(session):
    """Start Report Portal launch.

    This method is called every time on control or worker process start, it
    analyses from which process it is called and starts a Report Portal launch
    if it's a control process.
    :param session: Object of the pytest Session class
    """
    config = session.config
    if not config._rp_enabled:
        return

    try:
        config.py_test_service.start()
    except ResponseError as response_error:
        log.warning('Failed to initialize reportportal-client service. '
                    'Reporting is disabled.')
        log.debug(str(response_error))
        config.py_test_service.rp = None
        config._rp_enabled = False
        return

    if is_control(config):
        config.py_test_service.start_launch()
        if config.pluginmanager.hasplugin('xdist') \
                or config.pluginmanager.hasplugin('pytest-parallel'):
            if not wait_launch(session.config.py_test_service.rp):
                log.error(FAILED_LAUNCH_WAIT)
                config.py_test_service.rp = None
                config._rp_enabled = False


def pytest_collection_finish(session):
    """Collect tests if session is configured.

    :param session: Object of the pytest Session class
    """
    # noinspection PyProtectedMember
    if not session.config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return

    session.config.py_test_service.collect_tests(session)


# noinspection PyProtectedMember
def pytest_sessionfinish(session):
    """Finish current test session.

    :param session: Object of the pytest Session class
    """
    config = session.config
    if not config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return

    config.py_test_service.finish_suites()
    if is_control(config):
        config.py_test_service.finish_launch()

    config.py_test_service.stop()


def register_markers(config):
    """Register plugin's markers, to avoid declaring them in `pytest.ini`.

    :param config: Object of the pytest Config class
    """
    config.addinivalue_line(
        "markers", "issue(issue_id, reason, issue_type, url): mark test with "
                   "information about skipped or failed result"
    )
    config.addinivalue_line(
        "markers", "tc_id(id, parameterized, params): report the test"
                   "case with a custom Test Case ID. Parameters: \n"
                   "parameterized [True / False] - use parameter values in "
                   "Test Case ID generation \n"
                   "params [parameter names as list] - use only specified"
                   "parameters"
    )


def check_connection(agent_config):
    """Check connection to RP using provided options.

    If connection is successful returns True either False.
    :param agent_config: Instance of the AgentConfig class
    :return True on successful connection check, either False
    """
    url = '{0}/api/v1/project/{1}'.format(agent_config.rp_endpoint,
                                          agent_config.rp_project)
    headers = {'Authorization': 'bearer {0}'.format(agent_config.rp_api_key)}
    try:
        resp = requests.get(url, headers=headers,
                            verify=agent_config.rp_verify_ssl)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        log.exception(exc)
        log.error("Unable to connect to Report Portal, the launch won't be"
                  " reported")
        return False


# noinspection PyProtectedMember
def pytest_configure(config):
    """Update Config object with attributes required for reporting to RP.

    :param config: Object of the pytest Config class
    """
    register_markers(config)

    config._rp_enabled = not (
            config.getoption('--collect-only', default=False) or
            config.getoption('--setup-plan', default=False) or
            not config.option.rp_enabled)
    if not config._rp_enabled:
        return

    agent_config = AgentConfig(config)

    cond = (agent_config.rp_project, agent_config.rp_endpoint,
            agent_config.rp_api_key)
    config._rp_enabled = all(cond)
    if not config._rp_enabled:
        log.debug(MANDATORY_PARAMETER_MISSED_PATTERN.format(*cond))
        log.debug('Disabling reporting to RP.')
        return

    if not agent_config.rp_skip_connection_test:
        config._rp_enabled = check_connection(agent_config)

    if not config._rp_enabled:
        log.debug('Failed to establish connection with RP. '
                  'Disabling reporting.')
        return

    config._reporter_config = agent_config

    if is_control(config):
        config.py_test_service = PyTestServiceClass(agent_config)
    else:
        # noinspection PyUnresolvedReferences
        config.py_test_service = pickle.loads(config.workerinput['py_test_service'])


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtestloop(session):
    """
    Control start and finish of all test items in the session.

    :param session: pytest.Session
    :return:     generator object
    """
    config = session.config
    if not config._rp_enabled:
        yield
        return

    agent_config = config._reporter_config
    with patching_thread_class(agent_config):
        yield


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    """
    Control start and finish of pytest items.

    :param item: Pytest.Item
    :return:     generator object
    """
    config = item.config
    if not config._rp_enabled:
        yield
        return

    service = config.py_test_service
    agent_config = config._reporter_config
    service.start_pytest_item(item)
    log_level = agent_config.rp_log_level or logging.NOTSET
    log_handler = RPLogHandler(level=log_level,
                               filter_client_logs=True,
                               endpoint=agent_config.rp_endpoint,
                               ignored_record_names=('reportportal_client',
                                                     'pytest_reportportal'))
    log_format = agent_config.rp_log_format
    if log_format:
        log_handler.setFormatter(logging.Formatter(log_format))
    with patching_logger_class():
        with _pytest.logging.catching_logs(log_handler, level=log_level):
            yield
    service.finish_pytest_item(item)


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    """
        Change runtest_makereport function.

    :param item: pytest.Item
    :return: None
    """
    config = item.config
    if not config._rp_enabled:
        yield
        return

    report = (yield).get_result()
    service = item.config.py_test_service
    service.process_results(item, report)


def pytest_addoption(parser):
    """Add support for the RP-related options.

    :param parser: Object of the Parser class
    """
    group = parser.getgroup('reporting')

    def add_shared_option(name, help_str, default=None, action='store'):
        """
        Add an option to both the command line and the .ini file.

        This function modifies `parser` and `group` from the outer scope.

        :param name:     name of the option
        :param help_str: help message
        :param default:  default value
        :param action:   `group.addoption` action
        """
        parser.addini(
            name=name,
            default=default,
            help=help_str,
        )
        group.addoption(
            '--{0}'.format(name.replace('_', '-')),
            action=action,
            dest=name,
            help='{help} (overrides {name} config option)'.format(
                help=help_str,
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
        help_str='Launch name',
        default='Pytest Launch',
    )
    add_shared_option(
        name='rp_launch_id',
        help_str='Use already existing launch-id. The plugin won\'t control '
        'the Launch status',
    )
    add_shared_option(
        name='rp_launch_description',
        help_str='Launch description',
        default='',
    )
    add_shared_option(name='rp_project', help_str='Project name')
    add_shared_option(
        name='rp_log_level',
        help_str='Logging level for automated log records reporting',
    )
    add_shared_option(
        name='rp_log_format',
        help_str='Logging format for automated log records reporting',
    )
    add_shared_option(
        name='rp_rerun',
        help_str='Marks the launch as a rerun',
        default=False,
        action='store_true',
    )
    add_shared_option(
        name='rp_rerun_of',
        help_str='ID of the launch to be marked as a rerun (use only with '
                 'rp_rerun=True)',
        default='',
    )
    add_shared_option(
        name='rp_parent_item_id',
        help_str='Create all test item as child items of the given (already '
                 'existing) item.',
    )
    add_shared_option(name='rp_uuid', help_str='Deprecated: use `rp_api_key` '
                      'instead.')
    add_shared_option(
        name='rp_api_key',
        help_str='API key of Report Portal. Usually located on UI profile '
                 'page.'
    )
    add_shared_option(name='rp_endpoint', help_str='Server endpoint')
    add_shared_option(
        name='rp_mode',
        help_str='Visibility of current launch [DEFAULT, DEBUG]',
        default='DEFAULT'
    )
    add_shared_option(
        name='rp_thread_logging',
        help_str='EXPERIMENTAL: Report logs from threads. '
                 'This option applies a patch to the builtin Thread class, '
                 'and so it is turned off by default. Use with caution.',
        default=False,
        action='store_true'
    )
    add_shared_option(
        name='rp_launch_uuid_print',
        help_str='Enables printing Launch UUID on test run start. Possible values: [True, False]'
    )
    add_shared_option(
        name='rp_launch_uuid_print_output',
        help_str='Launch UUID print output. Default `stdout`. Possible values: [stderr, stdout]'
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
        'rp_log_batch_payload_size',
        default=str(MAX_LOG_BATCH_PAYLOAD_SIZE),
        help='Maximum payload size in bytes of async batch log requests')
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
        'rp_hierarchy_code',
        default=False,
        type='bool',
        help='Enables hierarchy for code')
    parser.addini(
        'rp_hierarchy_dirs_level',
        default='0',
        help='Directory starting hierarchy level')
    parser.addini(
        'rp_hierarchy_dirs',
        default=False,
        type='bool',
        help='Enables hierarchy for directories')
    parser.addini(
        'rp_hierarchy_dir_path_separator',
        default=os.path.sep,
        help='Path separator to display directories in test hierarchy')
    parser.addini(
        'rp_issue_system_url',
        default='',
        help='URL to get issue description. Issue id '
             'from pytest mark will be added to this URL')
    parser.addini(
        'rp_bts_project',
        default='',
        help='Bug-tracking system project as it configured on Report Portal '
             'server. To enable runtime external issue reporting you need to '
             'specify this and "rp_bts_url" property.')
    parser.addini(
        'rp_bts_url',
        default='',
        help='URL of bug-tracking system as it configured on Report Portal '
             'server. To enable runtime external issue reporting you need to '
             'specify this and "rp_bts_project" property.')
    parser.addini(
        'rp_verify_ssl',
        default='True',
        help='True/False - verify HTTPS calls, or path to a CA_BUNDLE or '
             'directory with certificates of trusted CAs.')
    parser.addini(
        'rp_issue_id_marks',
        type='bool',
        default=True,
        help='Add tag with issue id to the test')
    parser.addini(
        'retries',
        default='0',
        help='Deprecated: use `rp_api_retries` instead')
    parser.addini(
        'rp_api_retries',
        default='0',
        help='Amount of retries for performing REST calls to RP server')
    parser.addini(
        'rp_skip_connection_test',
        default=False,
        type='bool',
        help='Skip Report Portal connection test')
    parser.addini(
        'rp_launch_timeout',
        default=86400,
        help='Maximum time to wait for child processes finish, default value: '
             '86400 seconds (1 day)'
    )
    parser.addini(
        'rp_client_type',
        help='Type of the under-the-hood ReportPortal client implementation. Possible values: [SYNC, ASYNC_THREAD, '
             'ASYNC_BATCHED]'
    )
    parser.addini(
        'rp_connect_timeout',
        help='Connection timeout to ReportPortal server'
    )
    parser.addini(
        'rp_read_timeout',
        help='Response read timeout for ReportPortal connection'
    )
