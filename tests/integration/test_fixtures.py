#  Copyright 2024 EPAM Systems
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from collections import defaultdict
from unittest import mock

import pytest
from reportportal_client import set_current
from reportportal_client.steps import StepReporter

from examples.fixtures.test_fixture_setup.conftest import LOG_MESSAGE_SETUP as SINGLE_SETUP_MESSAGE
from examples.fixtures.test_fixture_setup_failure.conftest import LOG_MESSAGE_SETUP as LOG_MESSAGE_SETUP_FAILURE
from examples.fixtures.test_fixture_teardown.conftest import LOG_MESSAGE_BEFORE_YIELD, LOG_MESSAGE_TEARDOWN
from examples.fixtures.test_fixture_teardown_failure.conftest import (
    LOG_MESSAGE_BEFORE_YIELD as LOG_MESSAGE_BEFORE_YIELD_FAILURE, LOG_MESSAGE_TEARDOWN as LOG_MESSAGE_TEARDOWN_FAILURE)
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


ITEM_ID_DICT = defaultdict(lambda: 0)
ITEM_ID_LIST = []


def generate_item_id(*args, **kwargs) -> str:
    if args:
        name = args[0]
    else:
        name = kwargs['name']
    ITEM_ID_DICT[name] += 1
    item_id = f'{name}_{ITEM_ID_DICT[name]}'
    ITEM_ID_LIST.append(item_id)
    return item_id


def get_last_item_id() -> str:
    return ITEM_ID_LIST[-1]


def remove_last_item_id(*_, **__) -> str:
    if len(ITEM_ID_LIST) > 0:
        return ITEM_ID_LIST.pop()


@pytest.mark.parametrize('switch', [True, False])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_on_off(mock_client_init, switch):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)

    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = switch
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_teardown'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    expected_count = 3 if switch else 1
    assert start_count == finish_count == expected_count, \
        'Incorrect number of "start_test_item" or "finish_test_item" calls'


@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_setup(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    set_current(mock_client)
    mock_client.start_test_item.side_effect = generate_item_id
    mock_client.finish_test_item.side_effect = remove_last_item_id
    mock_client.current_item.side_effect = get_last_item_id

    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = True
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_setup'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    assert start_count == finish_count == 3, 'Incorrect number of "start_test_item" or "finish_test_item" calls'

    call_args = mock_client.start_test_item.call_args_list
    setup_call_args = call_args[1][0]
    step_name = 'function fixture setup: fixture_setup_config'
    assert setup_call_args[0] == step_name

    setup_call_kwargs = call_args[1][1]
    assert not setup_call_kwargs['has_stats']

    teardown_call_args = call_args[-1][0]
    assert teardown_call_args[0] == 'function fixture teardown: fixture_setup_config'

    setup_call_kwargs = call_args[-1][1]
    assert not setup_call_kwargs['has_stats']

    log_count = mock_client.log.call_count
    assert log_count == 1, 'Incorrect number of "log" calls'

    log_call_args_list = mock_client.log.call_args_list
    log_call_args = log_call_args_list[0][0]
    log_call_kwargs = log_call_args_list[0][1]

    assert log_call_args[1] == SINGLE_SETUP_MESSAGE
    assert log_call_kwargs['item_id'] == f'{step_name}_1'


@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_teardown(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    set_current(mock_client)
    mock_client.start_test_item.side_effect = generate_item_id
    mock_client.finish_test_item.side_effect = remove_last_item_id
    mock_client.current_item.side_effect = get_last_item_id

    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = True
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_teardown'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    assert start_count == finish_count == 3, 'Incorrect number of "start_test_item" or "finish_test_item" calls'

    call_args = mock_client.start_test_item.call_args_list
    setup_call_args = call_args[1][0]
    setup_step_name = 'function fixture setup: fixture_teardown_config'
    assert setup_call_args[0] == setup_step_name

    setup_call_kwargs = call_args[1][1]
    assert not setup_call_kwargs['has_stats']

    teardown_call_args = call_args[-1][0]
    teardown_step_name = 'function fixture teardown: fixture_teardown_config'
    assert teardown_call_args[0] == teardown_step_name

    setup_call_kwargs = call_args[-1][1]
    assert not setup_call_kwargs['has_stats']

    log_count = mock_client.log.call_count
    assert log_count == 2, 'Incorrect number of "log" calls'

    log_call_args_list = mock_client.log.call_args_list
    log_call_args = log_call_args_list[0][0]
    log_call_kwargs = log_call_args_list[0][1]

    assert log_call_args[1] == LOG_MESSAGE_BEFORE_YIELD
    assert log_call_kwargs['item_id'] == f'{setup_step_name}_1'

    log_call_args = log_call_args_list[-1][0]
    log_call_kwargs = log_call_args_list[-1][1]

    assert log_call_args[1] == LOG_MESSAGE_TEARDOWN
    assert log_call_kwargs['item_id'] == \
           'examples/fixtures/test_fixture_teardown/test_fixture_teardown.py::test_fixture_teardown_1'


@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_setup_failure(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    set_current(mock_client)
    mock_client.start_test_item.side_effect = generate_item_id
    mock_client.finish_test_item.side_effect = remove_last_item_id
    mock_client.current_item.side_effect = get_last_item_id

    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = True
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_setup_failure'], variables=variables)
    assert int(result) == 1, 'Exit code should be 1 (test failure)'

    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    assert start_count == finish_count == 2, 'Incorrect number of "start_test_item" or "finish_test_item" calls'

    call_args = mock_client.start_test_item.call_args_list
    setup_call_args = call_args[1][0]
    step_name = 'function fixture setup: fixture_setup_failure_config'
    assert setup_call_args[0] == step_name

    setup_call_kwargs = call_args[1][1]
    assert not setup_call_kwargs['has_stats']

    log_count = mock_client.log.call_count
    assert log_count == 2, 'Incorrect number of "log" calls'

    log_call_args_list = mock_client.log.call_args_list
    log_call_args = log_call_args_list[0][0]
    log_call_kwargs = log_call_args_list[0][1]

    assert log_call_args[1] == LOG_MESSAGE_SETUP_FAILURE
    assert log_call_kwargs['item_id'] == f'{step_name}_1'

    log_call_kwargs = log_call_args_list[1][1]

    assert log_call_kwargs['message'].endswith(
        'examples/fixtures/test_fixture_setup_failure/conftest.py:30: Exception')
    assert log_call_kwargs['item_id'] == \
           'examples/fixtures/test_fixture_setup_failure/test_fixture_setup_failure.py::test_fixture_setup_failure_1'


@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_teardown_failure(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    set_current(mock_client)
    mock_client.start_test_item.side_effect = generate_item_id
    mock_client.finish_test_item.side_effect = remove_last_item_id
    mock_client.current_item.side_effect = get_last_item_id

    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = True
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_teardown_failure'], variables=variables)
    assert int(result) == 1, 'Exit code should be 1 (test failure)'

    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    assert start_count == finish_count == 3, 'Incorrect number of "start_test_item" or "finish_test_item" calls'

    call_args = mock_client.start_test_item.call_args_list
    setup_call_args = call_args[1][0]
    setup_step_name = 'function fixture setup: fixture_teardown_failure_config'
    assert setup_call_args[0] == setup_step_name

    setup_call_kwargs = call_args[1][1]
    assert not setup_call_kwargs['has_stats']

    teardown_call_args = call_args[-1][0]
    teardown_step_name = 'function fixture teardown: fixture_teardown_failure_config'
    assert teardown_call_args[0] == teardown_step_name

    setup_call_kwargs = call_args[-1][1]
    assert not setup_call_kwargs['has_stats']

    log_count = mock_client.log.call_count
    assert log_count == 3, 'Incorrect number of "log" calls'

    log_call_args_list = mock_client.log.call_args_list
    log_call_args = log_call_args_list[0][0]
    log_call_kwargs = log_call_args_list[0][1]

    assert log_call_args[1] == LOG_MESSAGE_BEFORE_YIELD_FAILURE
    assert log_call_kwargs['item_id'] == f'{setup_step_name}_1'

    log_call_args = log_call_args_list[1][0]
    log_call_kwargs = log_call_args_list[1][1]

    assert log_call_args[1] == LOG_MESSAGE_TEARDOWN_FAILURE
    assert log_call_kwargs['item_id'] == \
           ('examples/fixtures/test_fixture_teardown_failure/test_fixture_teardown_failure.py::'
            'test_fixture_teardown_failure_1')

    log_call_kwargs = log_call_args_list[2][1]

    assert log_call_kwargs['message'].endswith(
        'examples/fixtures/test_fixture_teardown_failure/conftest.py:34: Exception')
    assert log_call_kwargs['item_id'] == \
           ('examples/fixtures/test_fixture_teardown_failure/test_fixture_teardown_failure.py::'
            'test_fixture_teardown_failure_1')
