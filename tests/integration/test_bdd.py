#  Copyright 2025 EPAM Systems
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

from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
def test_bdd(mock_client_init):
    variables = {}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count == 6, 'There should be exactly six "start_test_item" calls'
    assert mock_client.start_test_item.call_count == mock_client.finish_test_item.call_count, \
        '"start_test_item" and "finish_test_item" should be called the same number of times'


    # Check that scenarios and steps are reported correctly
    scenario_calls = [call for call in mock_client.start_test_item.call_args_list if call[1]['item_type'] == 'SCENARIO']
    step_calls = [call for call in mock_client.start_test_item.call_args_list if call[1]['item_type'] == 'STEP']
    assert len(scenario_calls) == 1, "There should be exactly one Scenario reported"
    assert len(step_calls) == 4, "There should be exactly four Steps reported"
