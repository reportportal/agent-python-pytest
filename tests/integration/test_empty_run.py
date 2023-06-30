"""This module includes integration tests for the empty run."""

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
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

from delayed_assert import expect, assert_expectations
from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
def test_empty_run(mock_client_init):
    """Verify that RP plugin does not fail if there is not tests in run.

    :param mock_client_init: Pytest fixture
    """
    result = utils.run_pytest_tests(tests=['examples/empty/'])

    assert int(result) == 5, 'Exit code should be 5 (no tests)'

    mock_client = mock_client_init.return_value
    expect(mock_client.start_launch.call_count == 1,
           '"start_launch" method was not called')
    expect(mock_client.finish_launch.call_count == 1,
           '"finish_launch" method was not called')
    assert_expectations()

    finish_args = mock_client.finish_launch.call_args_list
    expect('status' not in finish_args[0][1],
           'Launch status should not be defined')
    launch_end_time = finish_args[0][1]['end_time']
    expect(launch_end_time is not None and int(launch_end_time) > 0,
           'Launch end time is empty')
    assert_expectations()
