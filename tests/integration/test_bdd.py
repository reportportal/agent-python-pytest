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

from reportportal_client.steps import StepReporter

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


def setup_mock(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    return mock_client


@mock.patch(REPORT_PORTAL_SERVICE)
def test_bdd(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    variables = {}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    assert mock_client.start_test_item.call_count == 5, 'There should be exactly six "start_test_item" calls'
    assert (
        mock_client.start_test_item.call_count == mock_client.finish_test_item.call_count
    ), '"start_test_item" and "finish_test_item" should be called the same number of times'

    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["item_type"] == "STEP", "First call should be a Scenario"
    assert scenario_call[1].get("has_stats", True) is True, "First call should have stats"

    step_calls = mock_client.start_test_item.call_args_list[1:]
    for call in step_calls:
        assert call[0][2] == "step", "All other calls should be Steps"
        assert call[1]["has_stats"] is False, "All other calls should not have stats"

    assert (
        scenario_call[1]["code_ref"]
        == "features/arguments_four_steps.feature/[SCENARIO:Arguments for given, when, and, then]"
    )
