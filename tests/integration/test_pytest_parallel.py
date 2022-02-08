"""This module includes integration tests for "pytest_parallel" plugin."""

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

from delayed_assert import expect, assert_expectations
from six.moves import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils
from tests.helpers.utils import item_id_gen


@mock.patch(REPORT_PORTAL_SERVICE)
def test_pytest_parallel_threads(mock_client_init):
    """Verify "pytest_parallel" plugin run tests in two threads.

    :param mock_client_init: Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = item_id_gen

    result = utils.run_pytest_tests(tests=['examples/hierarchy'],
                                    args=['--tests-per-worker', '2'])
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value

    expect(mock_client.start_launch.call_count == 1,
           '"start_launch" method was not called')
    expect(mock_client.finish_launch.call_count == 1,
           '"finish_launch" method was not called')
    start_item_called = mock_client.start_test_item.call_count
    expect(start_item_called == 15,
           '"start_test_item" method was called incorrect number of times: ' +
           str(start_item_called))

    finish_item_called = mock_client.finish_test_item.call_count
    expect(finish_item_called == 15,
           '"finish_test_item" method was called incorrect number of times: ' +
           str(finish_item_called))
    assert_expectations()

    finish_args = mock_client.finish_launch.call_args_list
    expect(finish_args[0][1]['status'] in ('PASSED', None), 'Launch failed')
    launch_end_time = finish_args[0][1]['end_time']
    expect(launch_end_time is not None and int(launch_end_time) > 0,
           'Launch end time is empty')
    assert_expectations()
