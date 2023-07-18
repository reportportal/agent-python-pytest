"""This module includes integration tests for configuration parameters."""
#  Copyright (c) 2022 https://reportportal.io .
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

import sys
import warnings
from io import StringIO

from delayed_assert import expect, assert_expectations
from unittest import mock

from examples.test_rp_logging import LOG_MESSAGE
from pytest_reportportal.config import OUTPUT_TYPES
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils

TEST_LAUNCH_ID = 'test_launch_id'


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_launch_id(mock_client_init):
    """Verify that RP plugin does not start/stop launch if 'rp_launch_id' set.

    :param mock_client_init: Pytest fixture
    """
    variables = dict()
    variables['rp_launch_id'] = TEST_LAUNCH_ID
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'],
                                    variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expect(
        mock_client_init.call_args_list[0][1]['launch_id'] == TEST_LAUNCH_ID)

    mock_client = mock_client_init.return_value
    expect(mock_client.start_launch.call_count == 0,
           '"start_launch" method was called')
    expect(mock_client.finish_launch.call_count == 0,
           '"finish_launch" method was called')

    start_call_args = mock_client.start_test_item.call_args_list
    finish_call_args = mock_client.finish_test_item.call_args_list

    expect(len(start_call_args) == len(finish_call_args))
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_parent_item_id(mock_client_init):
    """Verify RP set Parent ID for root items if 'rp_parent_item_id' set.

    :param mock_client_init: Pytest fixture
    """
    parent_id = "parent_id"
    variables = dict()
    variables['rp_parent_item_id'] = parent_id
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'],
                                    variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    expect(mock_client.start_launch.call_count == 1,
           '"start_launch" method was not called')
    expect(mock_client.finish_launch.call_count == 1,
           '"finish_launch" method was not called')

    start_call_args = mock_client.start_test_item.call_args_list
    finish_call_args = mock_client.finish_test_item.call_args_list

    expect(len(start_call_args) == len(finish_call_args))
    expect(start_call_args[0][1]["parent_item_id"] == parent_id)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_parent_item_id_and_rp_launch_id(mock_client_init):
    """Verify RP handles both conf props 'rp_parent_item_id' & 'rp_launch_id'.

    :param mock_client_init: Pytest fixture
    """
    parent_id = "parent_id"
    variables = dict()
    variables['rp_parent_item_id'] = parent_id
    variables['rp_launch_id'] = "test_launch_id"
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'],
                                    variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    expect(mock_client.start_launch.call_count == 0,
           '"start_launch" method was called')
    expect(mock_client.finish_launch.call_count == 0,
           '"finish_launch" method was called')

    start_call_args = mock_client.start_test_item.call_args_list
    finish_call_args = mock_client.finish_test_item.call_args_list

    expect(len(start_call_args) == len(finish_call_args))
    expect(start_call_args[0][1]["parent_item_id"] == parent_id)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_log_format(mock_client_init):
    log_format = '(%(name)s) %(message)s (%(filename)s:%(lineno)s)'
    variables = {'rp_log_format': log_format}
    variables.update(utils.DEFAULT_VARIABLES.items())

    mock_client = mock_client_init.return_value
    result = utils.run_tests_with_client(
        mock_client, ['examples/test_rp_logging.py'], variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expect(mock_client.log.call_count == 1)
    message = mock_client.log.call_args_list[0][0][1]
    expect(len(message) > 0)
    expect(message == f'(examples.test_rp_logging) {LOG_MESSAGE} (test_rp_logging.py:24)')
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_log_batch_payload_size(mock_client_init):
    log_size = 123456
    variables = {'rp_log_batch_payload_size': log_size}
    variables.update(utils.DEFAULT_VARIABLES.items())

    result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                    variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expect(mock_client_init.call_count == 1)

    constructor_args = mock_client_init.call_args_list[0][1]
    expect(constructor_args['log_batch_payload_size'] == log_size)
    assert_expectations()


def filter_agent_call(warn):
    category = getattr(warn, 'category', None)
    if category:
        return category.__name__ == 'DeprecationWarning' or category.__name__ == 'RuntimeWarning'
    return False


def filter_agent_calls(warning_list):
    return list(
        filter(
            lambda call: filter_agent_call(call),
            warning_list
        )
    )


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_api_key(mock_client_init):
    api_key = 'rp_api_key'
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key': api_key}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 1)

        constructor_args = mock_client_init.call_args_list[0][1]
        expect(constructor_args['api_key'] == api_key)
        expect(len(filter_agent_calls(w)) == 0)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_uuid(mock_client_init):
    api_key = 'rp_api_key'
    variables = dict(utils.DEFAULT_VARIABLES)
    del variables['rp_api_key']
    variables.update({'rp_uuid': api_key}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 1)

        constructor_args = mock_client_init.call_args_list[0][1]
        expect(constructor_args['api_key'] == api_key)
        expect(len(filter_agent_calls(w)) == 1)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_api_key_priority(mock_client_init):
    api_key = 'rp_api_key'
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key': api_key, 'rp_uuid': 'rp_uuid'}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 1)

        constructor_args = mock_client_init.call_args_list[0][1]
        expect(constructor_args['api_key'] == api_key)
        expect(len(filter_agent_calls(w)) == 0)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_api_key_empty(mock_client_init):
    api_key = ''
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key': api_key}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 0)
        expect(len(filter_agent_calls(w)) == 1)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_api_retries(mock_client_init):
    retries = 5
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_retries': str(retries)}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 1)

        constructor_args = mock_client_init.call_args_list[0][1]
        expect(constructor_args['retries'] == retries)
        expect(len(filter_agent_calls(w)) == 0)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_retries(mock_client_init):
    retries = 5
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'retries': str(retries)}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
        assert int(result) == 0, 'Exit code should be 0 (no errors)'

        expect(mock_client_init.call_count == 1)

        constructor_args = mock_client_init.call_args_list[0][1]
        expect(constructor_args['retries'] == retries)
        expect(len(filter_agent_calls(w)) == 1)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_uuid_print': str(print_uuid)}.items())

    str_io = StringIO()
    stdout = sys.stdout
    try:
        OUTPUT_TYPES['stdout'] = str_io
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
    finally:
        OUTPUT_TYPES['stdout'] = stdout

    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] == print_uuid)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is str_io)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print_stderr(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_uuid_print': str(print_uuid), 'rp_launch_uuid_print_output': 'stderr'}.items())

    str_io = StringIO()
    stderr = sys.stderr
    try:
        OUTPUT_TYPES['stderr'] = str_io
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
    finally:
        OUTPUT_TYPES['stderr'] = stderr

    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] == print_uuid)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is str_io)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print_invalid_output(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_uuid_print': str(print_uuid), 'rp_launch_uuid_print_output': 'something'}.items())

    str_io = StringIO()
    stdout = sys.stdout
    try:
        OUTPUT_TYPES['stdout'] = str_io
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
    finally:
        OUTPUT_TYPES['stdout'] = stdout

    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] == print_uuid)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is str_io)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_no_launch_uuid_print(mock_client_init):
    variables = utils.DEFAULT_VARIABLES.copy()

    str_io = StringIO()
    stdout = sys.stdout
    try:
        OUTPUT_TYPES['stdout'] = str_io
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'],
                                        variables=variables)
    finally:
        OUTPUT_TYPES['stdout'] = stdout

    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] is False)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is str_io)
    assert_expectations()
