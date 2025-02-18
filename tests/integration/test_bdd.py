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

import importlib.metadata
from collections import defaultdict
from typing import Optional
from unittest import mock

from reportportal_client import set_current
from reportportal_client.steps import StepReporter

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils

pytest_bdd_version = [int(p) for p in importlib.metadata.version("pytest-bdd").split(".")]

ITEM_ID_DICT = defaultdict(lambda: 0)
ITEM_ID_LIST = []


def generate_item_id(*args, **kwargs) -> str:
    if args:
        name = args[0]
    else:
        name = kwargs["name"]
    ITEM_ID_DICT[name] += 1
    item_id = f"{name}_{ITEM_ID_DICT[name]}"
    ITEM_ID_LIST.append(item_id)
    return item_id


def get_last_item_id() -> Optional[str]:
    if len(ITEM_ID_LIST) > 0:
        return ITEM_ID_LIST[-1]


def remove_last_item_id(*_, **__) -> Optional[str]:
    if len(ITEM_ID_LIST) > 0:
        return ITEM_ID_LIST.pop()


def setup_mock(mock_client_init):
    mock_client = mock_client_init.return_value
    mock_client.step_reporter = StepReporter(mock_client)
    set_current(mock_client)
    return mock_client


def setup_mock_for_logging(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    mock_client.start_test_item.side_effect = generate_item_id
    mock_client.finish_test_item.side_effect = remove_last_item_id
    mock_client.current_item.side_effect = get_last_item_id
    return mock_client


STEP_NAMES = [
    "Given there are 5 cucumbers",
    "When I eat 3 cucumbers",
    "And I eat 2 cucumbers",
    "Then I should have 0 cucumbers",
]


@mock.patch(REPORT_PORTAL_SERVICE)
def test_basic_bdd(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    setup_mock_for_logging(mock_client_init)
    variables = {}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    assert mock_client.start_test_item.call_count == 5, 'There should be exactly five "start_test_item" calls'
    assert (
        mock_client.start_test_item.call_count == mock_client.finish_test_item.call_count
    ), '"start_test_item" and "finish_test_item" should be called the same number of times'

    scenario_call = mock_client.start_test_item.call_args_list[0]
    code_ref = "features/arguments_four_steps.feature/[SCENARIO:Arguments for given, when, and, then]"
    assert scenario_call[1]["item_type"] == "STEP", "First call should be a Scenario"
    assert scenario_call[1].get("has_stats", True) is True, "First call should have stats"
    assert scenario_call[1]["code_ref"] == code_ref
    assert scenario_call[1]["test_case_id"] == code_ref
    assert scenario_call[1]["name"] == "Feature: Four step arguments - Scenario: Arguments for given, when, and, then"
    assert scenario_call[1]["parent_item_id"] is None
    assert scenario_call[1]["parameters"] is None
    assert scenario_call[1]["description"] is None

    step_calls = mock_client.start_test_item.call_args_list[1:]
    for i, call in enumerate(step_calls):
        assert call[0][0] == STEP_NAMES[i]
        assert call[0][2] == "step", "All other calls should be Steps"
        assert call[1]["has_stats"] is False, "All other calls should not have stats"

    finish_calls = mock_client.finish_test_item.call_args_list
    finish_step_calls = finish_calls[:-1]
    for i, call in enumerate(finish_step_calls):
        assert call[0][0] == f"{STEP_NAMES[i]}_1"
        assert call[1]["status"] == "PASSED"
    finish_scenario_call = finish_calls[-1]
    assert finish_scenario_call[1]["status"] == "PASSED"
    assert (
        finish_scenario_call[1]["item_id"]
        == "Feature: Four step arguments - Scenario: Arguments for given, when, and, then_1"
    )


@mock.patch(REPORT_PORTAL_SERVICE)
def basic_bdd_with_feature_suite(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    setup_mock_for_logging(mock_client_init)
    variables = {"rp_hierarchy_code": True}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    assert mock_client.start_test_item.call_count == 6, 'There should be exactly six "start_test_item" calls'
    assert (
        mock_client.start_test_item.call_count == mock_client.finish_test_item.call_count
    ), '"start_test_item" and "finish_test_item" should be called the same number of times'

    suite_call = mock_client.start_test_item.call_args_list[0]
    assert suite_call[1]["item_type"] == "SUITE", "First call should be a Feature"
    assert suite_call[1].get("has_stats", True) is True, "First call should have stats"
    assert suite_call[1]["parent_item_id"] is None
    assert suite_call[1]["name"] == "Feature: Four step arguments"

    scenario_call = mock_client.start_test_item.call_args_list[1]
    code_ref = "features/arguments_four_steps.feature/[SCENARIO:Arguments for given, when, and, then]"
    assert scenario_call[1]["item_type"] == "STEP", "First call should be a Scenario"
    assert scenario_call[1].get("has_stats", True) is True, "First call should have stats"
    assert scenario_call[1]["code_ref"] == code_ref
    assert scenario_call[1]["test_case_id"] == code_ref
    assert scenario_call[1]["name"] == "Scenario: Arguments for given, when, and, then"
    assert scenario_call[1]["parent_item_id"] == "Feature: Four step arguments_1"
    assert scenario_call[1]["parameters"] is None
    assert scenario_call[1]["description"] is None

    step_calls = mock_client.start_test_item.call_args_list[2:]
    for call in step_calls:
        assert call[0][2] == "step", "All other calls should be Steps"
        assert call[1]["has_stats"] is False, "All other calls should not have stats"


@mock.patch(REPORT_PORTAL_SERVICE)
def bdd_scenario_descriptions(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    variables = {}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=["examples/bdd/step_defs/test_arguments_description.py"], variables=variables
    )
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    code_ref = "features/arguments_four_steps_description.feature/[SCENARIO:Arguments for given, when, and, then]"
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["code_ref"] == code_ref
    assert scenario_call[1]["test_case_id"] == code_ref
    description = scenario_call[1]["description"]
    if pytest_bdd_version[0] < 8:
        # before pytest-bdd 8 description was a list
        description = description[0]
    assert description == "Description for the scenario"


@mock.patch(REPORT_PORTAL_SERVICE)
def bdd_feature_descriptions(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    variables = {"rp_hierarchy_code": True}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=["examples/bdd/step_defs/test_arguments_description.py"], variables=variables
    )
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    feature_call = mock_client.start_test_item.call_args_list[0]
    assert feature_call[1]["description"] == "Description for the feature"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_bdd_failed_feature(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    setup_mock_for_logging(mock_client_init)
    variables = {}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_failed_step.py"], variables=variables)
    assert int(result) == 1, "Exit code should be 1 (test error)"

    assert mock_client.start_test_item.call_count == 2, 'There should be exactly two "start_test_item" calls'
    assert (
        mock_client.start_test_item.call_count == mock_client.finish_test_item.call_count
    ), '"start_test_item" and "finish_test_item" should be called the same number of times'

    finish_calls = mock_client.finish_test_item.call_args_list
    finish_step_call = finish_calls[0]
    finish_scenario_call = finish_calls[1]

    assert finish_step_call[0][0] == "Given I have a failed step_1"
    assert finish_step_call[1]["status"] == "FAILED"
    assert finish_scenario_call[1]["item_id"] == "Feature: Test failed scenario - Scenario: The scenario_1"
    assert finish_scenario_call[1]["status"] == "FAILED"
