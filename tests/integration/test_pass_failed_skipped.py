"""This module includes integration tests for item statuses report."""
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
import pytest
from delayed_assert import expect, assert_expectations
from six.moves import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@pytest.mark.parametrize(('test', 'expected_run_status',
                          'expected_item_statuses'), [
                             ('examples/test_simple.py', 0,
                              ['PASSED', 'PASSED', 'PASSED']),
                             ('examples/test_simple_fail.py', 1,
                              ['FAILED', 'FAILED', 'FAILED']),
                             ('examples/test_simple_skip.py', 0,
                              ['SKIPPED', 'PASSED', 'PASSED'])
                         ])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_simple_tests(mock_client_init, test, expected_run_status,
                      expected_item_statuses):
    """Verify a simple test creates correct structure and finishes all items.

    :param mock_client_init:       mocked Report Portal client Pytest fixture
    :param test:                   a test to run as use case
    :param expected_run_status:    expected pytest run status
    :param expected_item_statuses: expected result test item status
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen

    result = utils.run_pytest_tests(tests=[test])
    assert int(result) == expected_run_status, 'Exit code should be ' + str(
        expected_run_status)

    start_call_args = mock_client.start_test_item.call_args_list
    finish_call_args = mock_client.finish_test_item.call_args_list
    assert len(start_call_args) == len(finish_call_args), \
        'Number of started items should be equal to finished items'

    for i in range(len(start_call_args)):
        start_test_step = start_call_args[-1 - i][1]
        finish_test_step = finish_call_args[i][1]

        expect(finish_test_step['item_id'].startswith(start_test_step['name']))
        actual_status = finish_test_step['status']
        expect(actual_status == expected_item_statuses[i],
               'Invalid item status, actual "{}", expected: "{}"'
               .format(actual_status, expected_item_statuses[i]))
    assert_expectations()
