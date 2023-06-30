"""This module includes unit tests for the plugin."""

#  Copyright (c) 2021 http://reportportal.io .
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

from _pytest.config.argparsing import Parser
import pytest
from delayed_assert import expect, assert_expectations
from requests.exceptions import RequestException
# noinspection PyUnresolvedReferences
from unittest import mock

from reportportal_client.errors import ResponseError

from pytest_reportportal.config import AgentConfig
from pytest_reportportal.plugin import (
    is_control,
    log,
    pytest_addoption,
    pytest_configure,
    pytest_collection_finish,
    pytest_sessionstart,
    pytest_sessionfinish,
    wait_launch,
    MANDATORY_PARAMETER_MISSED_PATTERN, FAILED_LAUNCH_WAIT
)
from pytest_reportportal.service import PyTestServiceClass


def test_is_control(mocked_config):
    """Test is_master() function for the correct responses."""
    mocked_config.workerinput = None
    expect(is_control(mocked_config) is False)
    delattr(mocked_config, 'workerinput')
    expect(is_control(mocked_config) is True)
    assert_expectations()


@mock.patch('reportportal_client.logs.RPLogger.handle')
@pytest.mark.parametrize('log_level', ('info', 'debug', 'warning', 'error'))
def test_logger_handle_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels with some text attachment."""
    log_call = getattr(logger, log_level)
    attachment = 'Some {} attachment'.format(log_level)
    log_call("Some {} message".format(log_level), attachment=attachment)
    expect(mock_handler.call_count == 1,
           'logger.handle called more than 1 time')
    expect(getattr(mock_handler.call_args[0][0], "attachment") == attachment,
           'record.attachment in args doesn\'t match real value')
    assert_expectations()


@mock.patch('reportportal_client.logs.RPLogger.handle')
@pytest.mark.parametrize('log_level', ('info', 'debug', 'warning', 'error'))
def test_logger_handle_no_attachment(mock_handler, logger, log_level):
    """Test logger call for different log levels without any attachment."""
    log_call = getattr(logger, log_level)
    log_call('Some {} message'.format(log_level))
    expect(mock_handler.call_count == 1,
           'logger.handle called more than 1 time')
    expect(getattr(mock_handler.call_args[0][0], 'attachment') is None,
           'record.attachment in args is not None')
    assert_expectations()


@mock.patch('pytest_reportportal.plugin.requests.get', mock.Mock())
@mock.patch('pytest_reportportal.plugin.PyTestServiceClass')
def test_portal_on_maintenance(mocked_service_class, mocked_config,
                               mocked_session):
    """Test session configuration if RP is in maintenance mode.

    :param mocked_session: pytest fixture
    """
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_project = None

    mocked_service = mocked_service_class.return_value
    mocked_config.py_test_service = mocked_service
    mocked_service.start.side_effect = \
        ResponseError("<title>Report Portal - Maintenance</title>")
    pytest_sessionstart(mocked_session)
    assert mocked_config.py_test_service.rp is None


@mock.patch('pytest_reportportal.plugin.requests.Session.get', mock.Mock())
@mock.patch('pytest_reportportal.plugin.requests.get', mock.Mock())
def test_pytest_configure(mocked_config):
    """Test plugin successful configuration.

    :param mocked_config: Pytest fixture
    """
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_project = None
    pytest_configure(mocked_config)
    expect(mocked_config._rp_enabled is True)
    expect(
        lambda: isinstance(mocked_config.py_test_service, PyTestServiceClass))
    assert_expectations()
    mocked_config.getoption.assert_has_calls(
        [
            mock.call('--collect-only', default=False),
            mock.call('--setup-plan', default=False)
        ]
    )


@mock.patch('pytest_reportportal.plugin.requests.get')
def test_pytest_configure_dry_run(mocked_config):
    """Test plugin configuration in case of dry-run execution."""
    mocked_config.getoption.return_value = True
    pytest_configure(mocked_config)
    assert mocked_config._rp_enabled is False


@mock.patch('pytest_reportportal.plugin.requests.get', mock.Mock())
@mock.patch('pytest_reportportal.plugin.log', wraps=log)
def test_pytest_configure_misssing_rp_endpoint(mocked_log, mocked_config):
    """Test plugin configuration in case of missing rp_endpoint.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be changed to False, stopping plugin configuration, if
    rp_endpoint is not set.

    :param mocked_config: Pytest fixture
    """
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_endpoint = None
    mocked_config.getini.return_value = 0
    pytest_configure(mocked_config)
    assert mocked_config._rp_enabled is False
    mocked_log.debug.assert_has_calls(
        [
            mock.call(
                MANDATORY_PARAMETER_MISSED_PATTERN.format(
                    mocked_config.option.rp_project,
                    None,
                    mocked_config.option.rp_api_key,
                )),
            mock.call('Disabling reporting to RP.'),
        ]
    )


@mock.patch('pytest_reportportal.plugin.requests.get', mock.Mock())
@mock.patch('pytest_reportportal.plugin.log', wraps=log)
def test_pytest_configure_misssing_rp_project(mocked_log, mocked_config):
    """Test plugin configuration in case of missing rp_project.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be changed to False, stopping plugin configuration, if
    rp_project is not set.

    :param mocked_config: Pytest fixture
    """
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_project = None
    mocked_config.getini.return_value = 0
    pytest_configure(mocked_config)
    assert mocked_config._rp_enabled is False
    mocked_log.debug.assert_has_calls(
        [
            mock.call(
                MANDATORY_PARAMETER_MISSED_PATTERN.format(
                    None,
                    mocked_config.option.rp_endpoint,
                    mocked_config.option.rp_api_key,
                )),
            mock.call('Disabling reporting to RP.'),
        ]
    )


@mock.patch('pytest_reportportal.plugin.requests.get', mock.Mock())
@mock.patch('pytest_reportportal.plugin.log', wraps=log)
def test_pytest_configure_misssing_rp_uuid(mocked_log, mocked_config):
    """Test plugin configuration in case of missing rp_uuid.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be changed to False, stopping plugin configuration, if
    rp_uuid is not set.

    :param mocked_config: Pytest fixture
    """
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_api_key = None
    mocked_config.getini.return_value = 0
    pytest_configure(mocked_config)
    assert mocked_config._rp_enabled is False
    mocked_log.debug.assert_has_calls(
        [
            mock.call(
                MANDATORY_PARAMETER_MISSED_PATTERN.format(
                    mocked_config.option.rp_project,
                    mocked_config.option.rp_endpoint,
                    None,
                )),
            mock.call('Disabling reporting to RP.'),
        ]
    )


@mock.patch('pytest_reportportal.plugin.requests.get')
def test_pytest_configure_on_conn_error(mocked_get, mocked_config):
    """Test plugin configuration in case of HTTP error.

    The value of the _reportportal_configured attribute of the pytest Config
    object should be changed to False, stopping plugin configuration, if HTTP
    error occurs getting HTTP response from the ReportPortal.
    :param mocked_get:    Instance of the MagicMock
    :param mocked_config: Pytest fixture
    """
    mock_response = mock.Mock()
    mock_response.raise_for_status.side_effect = RequestException()
    mocked_get.return_value = mock_response
    mocked_config.option.rp_enabled = True
    mocked_config.option.rp_skip_connection_test = 'False'
    pytest_configure(mocked_config)
    assert mocked_config._rp_enabled is False


@mock.patch('pytest_reportportal.plugin.LAUNCH_WAIT_TIMEOUT', 1)
@mock.patch('pytest_reportportal.plugin.time')
def test_wait_launch(time_mock):
    """Test wait_launch() function for the correct behavior."""
    time_mock.time.side_effect = [0, 1, 2]
    rp_client = mock.Mock()
    rp_client.launch_id = None
    assert not wait_launch(rp_client)


def test_pytest_collection_finish(mocked_session):
    """Test collection_finish with the configured RP plugin.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.py_test_service = mock.Mock()
    pytest_collection_finish(mocked_session)
    mocked_session.config.py_test_service.collect_tests. \
        assert_called_with(mocked_session)


@mock.patch('pytest_reportportal.plugin.wait_launch',
            mock.Mock(return_value=True))
@mock.patch('pytest_reportportal.plugin.is_control', mock.Mock())
def test_pytest_sessionstart(mocked_session):
    """Test session configuration if RP plugin is correctly configured.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.pluginmanager.hasplugin.return_value = True
    mocked_session.config._reporter_config = mock.Mock(
        spec=AgentConfig(mocked_session.config))
    mocked_session.config._reporter_config.rp_launch_attributes = []
    mocked_session.config._reporter_config.rp_launch_id = None
    mocked_session.config.py_test_service = mock.Mock()
    pytest_sessionstart(mocked_session)
    expect(lambda: mocked_session.config.py_test_service.init_service.called)
    expect(lambda: mocked_session.config.py_test_service.rp is not None)
    expect(lambda: mocked_session.config._rp_enabled is True)
    expect(lambda: mocked_session.config.py_test_service.start_launch.called)

    assert_expectations()


@mock.patch('pytest_reportportal.plugin.log', wraps=log)
@mock.patch('pytest_reportportal.plugin.is_control', mock.Mock())
@mock.patch('pytest_reportportal.plugin.wait_launch',
            mock.Mock(return_value=False))
def test_pytest_sessionstart_launch_wait_fail(mocked_log, mocked_session):
    """Test session configuration if RP plugin is correctly configured.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.pluginmanager.hasplugin.return_value = True
    mocked_session.config._reporter_config = mock.Mock(
        spec=AgentConfig(mocked_session.config))
    mocked_session.config._reporter_config.rp_launch_attributes = []
    mocked_session.config._reporter_config.rp_launch_id = None
    mocked_session.config.py_test_service = mock.Mock()
    pytest_sessionstart(mocked_session)
    expect(lambda: mocked_session.config.py_test_service.rp is None)
    expect(lambda: mocked_session.config._rp_enabled is False)
    assert_expectations()
    mocked_log.error.assert_has_calls(
        [
            mock.call(FAILED_LAUNCH_WAIT)
        ]
    )


@mock.patch('pytest_reportportal.plugin.is_control', mock.Mock())
@mock.patch('pytest_reportportal.plugin.wait_launch', mock.Mock())
def test_pytest_sessionstart_with_launch_id(mocked_session):
    """Test session configuration if RP launch ID is set via command-line.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.pluginmanager.hasplugin.return_value = True
    mocked_session.config._reporter_config = mock.Mock(
        spec=AgentConfig(mocked_session.config))
    mocked_session.config._reporter_config.rp_launch_attributes = []
    mocked_session.config._reporter_config.rp_launch_id = 1
    mocked_session.config.py_test_service = mock.Mock()
    pytest_sessionstart(mocked_session)
    expect(lambda: mocked_session.config.py_test_service.start_launch.
           assert_not_called())
    assert_expectations()


@mock.patch('pytest_reportportal.plugin.is_control', mock.Mock())
def test_pytest_sessionfinish(mocked_session):
    """Test sessionfinish with the configured RP plugin.

    :param mocked_session: pytest fixture
    """
    mocked_session.config.py_test_service = mock.Mock()
    mocked_session.config._reporter_config.rp_launch_id = None
    pytest_sessionfinish(mocked_session)
    assert mocked_session.config.py_test_service.finish_launch.called


def test_pytest_addoption_adds_correct_ini_file_arguments():
    """Test the correct list of options are available in the .ini file."""
    expected_argument_names = (
        'rp_launch',
        'rp_launch_id',
        'rp_launch_description',
        'rp_project',
        'rp_log_level',
        'rp_log_format',
        'rp_rerun',
        'rp_rerun_of',
        'rp_parent_item_id',
        'rp_uuid',
        'rp_api_key',
        'rp_endpoint',
        'rp_mode',
        'rp_thread_logging',
        'rp_launch_uuid_print',
        'rp_launch_uuid_print_output',
        'rp_launch_attributes',
        'rp_tests_attributes',
        'rp_log_batch_size',
        'rp_log_batch_payload_size',
        'rp_ignore_attributes',
        'rp_is_skipped_an_issue',
        'rp_hierarchy_code',
        'rp_hierarchy_dirs_level',
        'rp_hierarchy_dirs',
        'rp_hierarchy_dir_path_separator',
        'rp_issue_system_url',
        'rp_bts_project',
        'rp_bts_url',
        'rp_verify_ssl',
        'rp_issue_id_marks',
        'retries',
        'rp_api_retries',
        'rp_skip_connection_test',
        'rp_launch_timeout'
    )
    mock_parser = mock.MagicMock(spec=Parser)

    pytest_addoption(mock_parser)

    added_argument_names = []
    for args, kwargs in mock_parser.addini.call_args_list:
        added_argument_names.append(args[0] if args else kwargs.get("name"))
    assert tuple(added_argument_names) == expected_argument_names


def test_pytest_addoption_adds_correct_command_line_arguments():
    """Test the correct list of options are available in the command line."""
    expected_argument_names = (
        '--reportportal',
        '--rp-launch',
        '--rp-launch-id',
        '--rp-launch-description',
        '--rp-project',
        '--rp-log-level',
        '--rp-log-format',
        '--rp-rerun',
        '--rp-rerun-of',
        '--rp-parent-item-id',
        '--rp-uuid',
        '--rp-api-key',
        '--rp-endpoint',
        '--rp-mode',
        '--rp-thread-logging',
        '--rp-launch-uuid-print',
        '--rp-launch-uuid-print-output'
    )
    mock_parser = mock.MagicMock(spec=Parser)
    mock_reporting_group = mock_parser.getgroup.return_value

    pytest_addoption(mock_parser)

    mock_parser.getgroup.assert_called_once_with("reporting")
    added_argument_names = []
    for args, kwargs in mock_reporting_group.addoption.call_args_list:
        added_argument_names.append(args[0] if args else kwargs.get("name"))
    assert tuple(added_argument_names) == expected_argument_names
