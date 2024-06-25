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

"""This module includes integration tests for configuration parameters."""

import warnings
from unittest import mock

import pytest
from delayed_assert import expect, assert_expectations
from reportportal_client import OutputType

from examples.test_rp_logging import LOG_MESSAGE
from tests import REPORT_PORTAL_SERVICE, REQUESTS_SERVICE
from tests.helpers import utils

TEST_LAUNCH_ID = 'test_launch_id'


@mock.patch(REQUESTS_SERVICE)
def test_rp_launch_forked_id(mock_requests_init):
    """Verify that RP plugin does not start/stop launch if 'rp_launch_forked_id' set.

    :param mock_requests_init: mocked requests lib
    """
    variables = dict()
    variables['rp_launch_forked_id'] = TEST_LAUNCH_ID
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_requests = mock_requests_init.return_value
    assert mock_requests.post.call_count == 1
    item_start = mock_requests.post.call_args_list[0]
    assert item_start[0][0].endswith('/item')
    assert item_start[1]['json']['launchUuid'] == TEST_LAUNCH_ID


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_parent_item_id(mock_client_init):
    """Verify RP set Parent ID for root items if 'rp_parent_item_id' set.

    :param mock_client_init: Pytest fixture
    """
    parent_id = "parent_id"
    variables = dict()
    variables['rp_parent_item_id'] = parent_id
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'], variables=variables)

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


@mock.patch(REQUESTS_SERVICE)
def test_rp_parent_item_id_and_rp_launch_forked_id(mock_requests_init):
    """Verify RP handles both conf props 'rp_parent_item_id' & 'rp_launch_forked_id'.

    :param mock_requests_init: mocked requests lib
    """
    parent_id = "parent_id"
    variables = dict()
    variables['rp_parent_item_id'] = parent_id
    variables['rp_launch_forked_id'] = TEST_LAUNCH_ID
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_requests = mock_requests_init.return_value
    assert mock_requests.post.call_count == 1
    item_start = mock_requests.post.call_args_list[0]
    assert item_start[0][0].endswith(f'/item/{parent_id}')
    assert item_start[1]['json']['launchUuid'] == TEST_LAUNCH_ID


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
def test_rp_log_batch_payload_size_forked(mock_client_init):
    log_size = 123456
    variables = {'rp_log_batch_payload_size_forked': log_size}
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
def test_rp_api_key_forked(mock_client_init):
    api_key = 'rp_api_key_forked'
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key_forked': api_key}.items())

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
    api_key = 'rp_api_key_forked'
    variables = dict(utils.DEFAULT_VARIABLES)
    del variables['rp_api_key_forked']
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
def test_rp_api_key_forked_priority(mock_client_init):
    api_key = 'rp_api_key_forked'
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key_forked': api_key, 'rp_uuid': 'rp_uuid'}.items())

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
def test_rp_api_key_forked_empty(mock_client_init):
    api_key = ''
    variables = dict(utils.DEFAULT_VARIABLES)
    variables.update({'rp_api_key_forked': api_key}.items())

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
        result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)
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
def test_rp_issue_system_url_warning(mock_client_init):
    url = 'https://bugzilla.some.com/show_bug.cgi?id={issue_id}'
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_issue_system_url': str(url)}.items())

    with warnings.catch_warnings(record=True) as w:
        result = utils.run_pytest_tests(['examples/test_issue_id.py'], variables=variables)
        assert int(result) == 1, 'Exit code should be 1 (test failure)'

        expect(mock_client_init.call_count == 1)
        expect(len(filter_agent_calls(w)) == 1)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_forked_uuid_print': str(print_uuid)}.items())
    result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] == print_uuid)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is None)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print_stderr(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_forked_uuid_print': str(print_uuid), 'rp_launch_forked_uuid_print_output': 'stderr'}.items())
    result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] == print_uuid)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is OutputType.STDERR)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_uuid_print_invalid_output(mock_client_init):
    print_uuid = True
    variables = utils.DEFAULT_VARIABLES.copy()
    variables.update({'rp_launch_forked_uuid_print': str(print_uuid), 'rp_launch_forked_uuid_print_output': 'something'}.items())
    result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)
    assert int(result) == 3, 'Exit code should be 3 (INTERNALERROR)'
    assert mock_client_init.call_count == 0


@mock.patch(REPORT_PORTAL_SERVICE)
def test_no_launch_uuid_print(mock_client_init):
    variables = utils.DEFAULT_VARIABLES.copy()
    result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    expect(mock_client_init.call_count == 1)
    expect(mock_client_init.call_args_list[0][1]['launch_uuid_print'] is False)
    expect(mock_client_init.call_args_list[0][1]['print_output'] is None)
    assert_expectations()


@pytest.mark.parametrize(
    'connect_value, read_value, expected_result',
    [
        ('5', '15', (5.0, 15.0)),
        ('5.5', '15.5', (5.5, 15.5)),
        (None, None, None),
        (None, '5', 5),
        ('5', None, 5)
    ]
)
@mock.patch(REPORT_PORTAL_SERVICE)
def test_client_timeouts(mock_client_init, connect_value, read_value, expected_result):
    variables = utils.DEFAULT_VARIABLES.copy()
    if connect_value:
        variables['rp_connect_timeout'] = connect_value
    if read_value:
        variables['rp_read_timeout'] = read_value

    result = utils.run_pytest_tests(['examples/test_rp_logging.py'], variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no errors)'
    assert mock_client_init.call_count == 1
    assert mock_client_init.call_args_list[0][1]['http_timeout'] == expected_result
