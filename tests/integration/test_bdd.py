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

import pytest
from reportportal_client import set_current
from reportportal_client.steps import StepReporter

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils

pytest_bdd_version = [int(p) for p in importlib.metadata.version("pytest-bdd").split(".")]

ITEM_ID_DICT = defaultdict(lambda: 0)
ITEM_ID_LIST = []


def generate_item_id(*args, **kwargs) -> str:
    global ITEM_ID_DICT
    global ITEM_ID_LIST
    if args:
        name = args[0]
    else:
        name = kwargs["name"]
    count = ITEM_ID_DICT[name]
    count += 1
    ITEM_ID_DICT[name] = count
    item_id = f"{name}_{count}"
    ITEM_ID_LIST.append(item_id)
    return item_id


def get_last_item_id() -> Optional[str]:
    global ITEM_ID_LIST
    if len(ITEM_ID_LIST) > 0:
        return ITEM_ID_LIST[-1]


def remove_last_item_id(*_, **__) -> Optional[str]:
    global ITEM_ID_LIST
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
def test_basic(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments.py"])
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
def test_basic_with_feature_suite(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
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
def test_scenario_descriptions(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_arguments_description.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    code_ref = "features/arguments_four_steps_description.feature/[SCENARIO:Arguments for given, when, and, then]"
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["code_ref"] == code_ref
    assert scenario_call[1]["test_case_id"] == code_ref
    description = scenario_call[1]["description"]
    assert description == "Description for the scenario"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_feature_descriptions(mock_client_init):
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
def test_failed_feature(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_failed_step.py"])
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

    log_count = mock_client.log.call_count
    # 1 - debug log from pytest-bdd's scenario module; 2 - traceback log from the agent; 3 - error log from pytest
    assert log_count == 1 + 1 + 1, 'Incorrect number of "log" calls'

    log_call_args_list = mock_client.log.call_args_list[1:]
    assert log_call_args_list[0][1]["level"] == "ERROR"
    assert log_call_args_list[0][1]["message"].endswith("AssertionError: assert False\n")
    assert log_call_args_list[0][1]["item_id"] == "Given I have a failed step_1"

    assert log_call_args_list[1][1]["level"] == "ERROR"
    assert log_call_args_list[1][1]["message"].endswith("AssertionError")
    assert log_call_args_list[1][1]["item_id"] == "Feature: Test failed scenario - Scenario: The scenario_1"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_attributes(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)

    test_file = "examples/bdd/step_defs/test_belly.py"
    result = utils.run_pytest_tests(tests=[test_file])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    scenario_call = mock_client.start_test_item.call_args_list[0]
    scenario_attrs = scenario_call[1].get("attributes", None)
    assert scenario_attrs is not None
    assert len(scenario_attrs) == 2
    assert {"value": "ok"} in scenario_attrs
    assert {"key": "key", "value": "value"} in scenario_attrs


@mock.patch(REPORT_PORTAL_SERVICE)
def test_feature_attributes(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)

    variables = {"rp_hierarchy_code": True}
    variables.update(utils.DEFAULT_VARIABLES.items())
    test_file = "examples/bdd/step_defs/test_belly.py"
    result = utils.run_pytest_tests(tests=[test_file], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    feature_call = mock_client.start_test_item.call_args_list[0]
    feature_attrs = feature_call[1].get("attributes", [])
    assert feature_attrs is not None
    assert len(feature_attrs) == 3
    assert {"value": "smoke"} in feature_attrs
    assert {"value": "test"} in feature_attrs
    assert {"key": "feature", "value": "belly"} in feature_attrs

    scenario_call = mock_client.start_test_item.call_args_list[1]
    scenario_attrs = scenario_call[1].get("attributes", [])
    assert scenario_attrs is not None
    assert len(scenario_attrs) == 2
    assert {"value": "ok"} in scenario_attrs
    assert {"key": "key", "value": "value"} in scenario_attrs


@mock.patch(REPORT_PORTAL_SERVICE)
def test_background_step(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)

    test_file = "examples/bdd/step_defs/test_background.py"
    result = utils.run_pytest_tests(tests=[test_file])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify the first scenario
    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    assert scenario_call_1[1]["name"] == "Feature: Test scenario with a background - Scenario: The first scenario"
    assert scenario_call_1[1]["item_type"] == "STEP"
    assert scenario_call_1[1].get("has_stats", True)

    # Verify the Background step for the first scenario
    background_call_1 = mock_client.start_test_item.call_args_list[1]
    assert background_call_1[0][0] == "Background"
    assert background_call_1[0][2] == "step"
    assert background_call_1[1]["has_stats"] is False
    assert background_call_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"

    # Verify the nested steps within the Background for the first scenario
    nested_step_call_1 = mock_client.start_test_item.call_args_list[2]
    assert nested_step_call_1[0][0] == "Given I have empty step"
    assert nested_step_call_1[0][2] == "step"
    assert nested_step_call_1[1]["parent_item_id"] == background_call_1[0][0] + "_1"
    assert nested_step_call_1[1]["has_stats"] is False

    # Verify the step within the first scenario
    scenario_step_call_1 = mock_client.start_test_item.call_args_list[3]
    assert scenario_step_call_1[0][0] == "Then I have another empty step"
    assert scenario_step_call_1[0][2] == "step"
    assert scenario_step_call_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert scenario_step_call_1[1]["has_stats"] is False

    # Verify the second scenario
    scenario_call_2 = mock_client.start_test_item.call_args_list[4]
    assert scenario_call_2[1]["name"] == "Feature: Test scenario with a background - Scenario: The second scenario"
    assert scenario_call_2[1]["item_type"] == "STEP"
    assert scenario_call_1[1].get("has_stats", True)

    # Verify the Background step for the second scenario
    background_call_2 = mock_client.start_test_item.call_args_list[5]
    assert background_call_2[0][0] == "Background"
    assert background_call_2[0][2] == "step"
    assert background_call_2[1]["has_stats"] is False
    assert background_call_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_1"

    # Verify the nested steps within the Background for the second scenario
    nested_step_call_2 = mock_client.start_test_item.call_args_list[6]
    assert nested_step_call_2[0][0] == "Given I have empty step"
    assert nested_step_call_2[0][2] == "step"
    assert nested_step_call_2[1]["parent_item_id"] == background_call_2[0][0] + "_2"
    assert nested_step_call_2[1]["has_stats"] is False

    # Verify the step within the second scenario
    scenario_step_call_2 = mock_client.start_test_item.call_args_list[7]
    assert scenario_step_call_2[0][0] == "Then I have one more empty step"
    assert scenario_step_call_2[0][2] == "step"
    assert scenario_step_call_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_1"
    assert scenario_step_call_2[1]["has_stats"] is False


@mock.patch(REPORT_PORTAL_SERVICE)
def test_background_two_steps(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)

    test_file = "examples/bdd/step_defs/test_background_two_steps.py"
    result = utils.run_pytest_tests(tests=[test_file])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify the scenario
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call[1]["name"] == "Feature: Test scenario with a background with two steps - Scenario: The scenario"
    )
    assert scenario_call[1]["item_type"] == "STEP"
    assert scenario_call[1].get("has_stats", True)

    # Verify the Background step
    background_call = mock_client.start_test_item.call_args_list[1]
    assert background_call[0][0] == "Background"
    assert background_call[0][2] == "step"
    assert background_call[1]["has_stats"] is False
    assert background_call[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"

    # Verify the first nested step within the Background
    nested_step_call_1 = mock_client.start_test_item.call_args_list[2]
    assert nested_step_call_1[0][0] == "Given I have first empty step"
    assert nested_step_call_1[0][2] == "step"
    assert nested_step_call_1[1]["parent_item_id"] == background_call[0][0] + "_3"
    assert nested_step_call_1[1]["has_stats"] is False

    # Verify the second nested step within the Background
    nested_step_call_2 = mock_client.start_test_item.call_args_list[3]
    assert nested_step_call_2[0][0] == "And I have second empty step"
    assert nested_step_call_2[0][2] == "step"
    assert nested_step_call_2[1]["parent_item_id"] == background_call[0][0] + "_3"
    assert nested_step_call_2[1]["has_stats"] is False

    # Verify the scenario step
    scenario_step_call = mock_client.start_test_item.call_args_list[4]
    assert scenario_step_call[0][0] == "Then I have main step"
    assert scenario_step_call[0][2] == "step"
    assert scenario_step_call[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"
    assert scenario_step_call[1]["has_stats"] is False


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_rule(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_rule_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario from first rule
    scenario_1_call = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_1_call[1]["name"]
        == "Feature: Test rule keyword - Rule: The first rule - Scenario: The first scenario"
    )
    assert scenario_1_call[1]["item_type"] == "STEP"
    assert scenario_1_call[1].get("has_stats", True) is True
    assert scenario_1_call[1]["parent_item_id"] is None
    assert (
        scenario_1_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The first rule]/[SCENARIO:The first scenario]"
    )

    # Verify first scenario steps
    step_1_given = mock_client.start_test_item.call_args_list[1]
    assert step_1_given[0][0] == "Given I have empty step"
    assert step_1_given[0][2] == "step"
    assert step_1_given[1]["parent_item_id"] == scenario_1_call[1]["name"] + "_1"
    assert step_1_given[1]["has_stats"] is False

    step_1_then = mock_client.start_test_item.call_args_list[2]
    assert step_1_then[0][0] == "Then I have another empty step"
    assert step_1_then[0][2] == "step"
    assert step_1_then[1]["parent_item_id"] == scenario_1_call[1]["name"] + "_1"
    assert step_1_then[1]["has_stats"] is False

    # Verify second scenario from first rule
    scenario_2_call = mock_client.start_test_item.call_args_list[3]
    assert (
        scenario_2_call[1]["name"]
        == "Feature: Test rule keyword - Rule: The first rule - Scenario: The second scenario"
    )
    assert scenario_2_call[1]["item_type"] == "STEP"
    assert scenario_2_call[1].get("has_stats", True) is True
    assert scenario_2_call[1]["parent_item_id"] is None
    assert (
        scenario_2_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The first rule]/[SCENARIO:The second scenario]"
    )

    # Verify second scenario steps
    step_2_given = mock_client.start_test_item.call_args_list[4]
    assert step_2_given[0][0] == "Given I have empty step"
    assert step_2_given[0][2] == "step"
    assert step_2_given[1]["parent_item_id"] == scenario_2_call[1]["name"] + "_1"
    assert step_2_given[1]["has_stats"] is False

    step_2_then = mock_client.start_test_item.call_args_list[5]
    assert step_2_then[0][0] == "Then I have one more empty step"
    assert step_2_then[0][2] == "step"
    assert step_2_then[1]["parent_item_id"] == scenario_2_call[1]["name"] + "_1"
    assert step_2_then[1]["has_stats"] is False

    # Verify third scenario from second rule
    scenario_3_call = mock_client.start_test_item.call_args_list[6]
    assert (
        scenario_3_call[1]["name"]
        == "Feature: Test rule keyword - Rule: The second rule - Scenario: The third scenario"
    )
    assert scenario_3_call[1]["item_type"] == "STEP"
    assert scenario_3_call[1].get("has_stats", True) is True
    assert scenario_3_call[1]["parent_item_id"] is None
    assert (
        scenario_3_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The second rule]/[SCENARIO:The third scenario]"
    )

    # Verify third scenario steps
    step_3_given = mock_client.start_test_item.call_args_list[7]
    assert step_3_given[0][0] == "Given I have empty step"
    assert step_3_given[0][2] == "step"
    assert step_3_given[1]["parent_item_id"] == scenario_3_call[1]["name"] + "_1"
    assert step_3_given[1]["has_stats"] is False

    step_3_then = mock_client.start_test_item.call_args_list[8]
    assert step_3_then[0][0] == "Then I have one more else empty step"
    assert step_3_then[0][2] == "step"
    assert step_3_then[1]["parent_item_id"] == scenario_3_call[1]["name"] + "_1"
    assert step_3_then[1]["has_stats"] is False

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_rule_hierarchy(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)

    variables = {"rp_hierarchy_code": True}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_rule_steps.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify Feature
    feature_call = mock_client.start_test_item.call_args_list[0]
    assert feature_call[1]["name"] == "Feature: Test rule keyword"
    assert feature_call[1]["item_type"] == "SUITE"
    assert feature_call[1].get("has_stats", True) is True
    assert feature_call[1]["parent_item_id"] is None
    feature_id = "Feature: Test rule keyword_1"

    # Verify first Rule
    rule_1_call = mock_client.start_test_item.call_args_list[1]
    assert rule_1_call[1]["name"] == "Rule: The first rule"
    assert rule_1_call[1]["item_type"] == "SUITE"
    assert rule_1_call[1].get("has_stats", True) is True
    assert rule_1_call[1]["parent_item_id"] == feature_id
    rule_1_id = "Rule: The first rule_1"

    # Verify first scenario under first rule
    scenario_1_call = mock_client.start_test_item.call_args_list[2]
    assert scenario_1_call[1]["name"] == "Scenario: The first scenario"
    assert scenario_1_call[1]["item_type"] == "STEP"
    assert scenario_1_call[1].get("has_stats", True) is True
    assert scenario_1_call[1]["parent_item_id"] == rule_1_id
    assert (
        scenario_1_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The first rule]/[SCENARIO:The first scenario]"
    )

    # Verify second scenario under first rule
    scenario_2_call = mock_client.start_test_item.call_args_list[5]
    assert scenario_2_call[1]["name"] == "Scenario: The second scenario"
    assert scenario_2_call[1]["item_type"] == "STEP"
    assert scenario_2_call[1].get("has_stats", True) is True
    assert scenario_2_call[1]["parent_item_id"] == rule_1_id
    assert (
        scenario_2_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The first rule]/[SCENARIO:The second scenario]"
    )

    # Verify second Rule
    rule_2_call = mock_client.start_test_item.call_args_list[8]
    assert rule_2_call[1]["name"] == "Rule: The second rule"
    assert rule_2_call[1]["item_type"] == "SUITE"
    assert rule_2_call[1].get("has_stats", True) is True
    assert rule_2_call[1]["parent_item_id"] == feature_id
    rule_2_id = "Rule: The second rule_1"

    # Verify third scenario under second rule
    scenario_3_call = mock_client.start_test_item.call_args_list[9]
    assert scenario_3_call[1]["name"] == "Scenario: The third scenario"
    assert scenario_3_call[1]["item_type"] == "STEP"
    assert scenario_3_call[1].get("has_stats", True) is True
    assert scenario_3_call[1]["parent_item_id"] == rule_2_id
    assert (
        scenario_3_call[1]["code_ref"]
        == "features/rule_keyword.feature/[RULE:The second rule]/[SCENARIO:The third scenario]"
    )


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_parameters(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_parameters_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario with parameters
    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call_1[1]["name"]
        == "Feature: Basic test with parameters - Scenario Outline: Test with different parameters"
    )
    assert scenario_call_1[1]["item_type"] == "STEP"
    assert scenario_call_1[1].get("has_stats", True)
    assert (
        scenario_call_1[1]["code_ref"]
        == "features/scenario_outline_parameters.feature/[EXAMPLE:Test with different parameters"
        '[parameters:123;str:"first"]]'
    )
    parameters = scenario_call_1[1]["parameters"].items()
    assert len(parameters) == 2
    assert ("str", '"first"') in parameters
    assert ("parameters", "123") in parameters
    assert scenario_call_1[1]["description"] is not None
    assert scenario_call_1[1]["description"].endswith('|\xa0"first"\xa0|\xa0\xa0\xa0\xa0123\xa0\xa0\xa0\xa0\xa0|')

    # Verify steps for first scenario
    given_step_1 = mock_client.start_test_item.call_args_list[1]
    assert given_step_1[0][0] == "Given It is test with parameters"
    assert given_step_1[0][2] == "step"
    assert given_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert given_step_1[1]["has_stats"] is False

    when_step_1 = mock_client.start_test_item.call_args_list[2]
    assert when_step_1[0][0] == 'When I have parameter "first"'
    assert when_step_1[0][2] == "step"
    assert when_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert when_step_1[1]["has_stats"] is False

    then_step_1 = mock_client.start_test_item.call_args_list[3]
    assert then_step_1[0][0] == "Then I emit number 123 on level info"
    assert then_step_1[0][2] == "step"
    assert then_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert then_step_1[1]["has_stats"] is False

    # Verify second scenario with parameters
    scenario_call_2 = mock_client.start_test_item.call_args_list[4]
    assert (
        scenario_call_2[1]["name"]
        == "Feature: Basic test with parameters - Scenario Outline: Test with different parameters"
    )
    assert scenario_call_2[1]["item_type"] == "STEP"
    assert scenario_call_2[1].get("has_stats", True)
    assert (
        scenario_call_2[1]["code_ref"]
        == "features/scenario_outline_parameters.feature/[EXAMPLE:Test with different parameters"
        '[parameters:12345;str:"second"]]'
    )
    parameters = scenario_call_2[1]["parameters"].items()
    assert len(parameters) == 2
    assert ("str", '"second"') in parameters
    assert ("parameters", "12345") in parameters
    assert scenario_call_2[1]["description"] is not None
    assert scenario_call_2[1]["description"].endswith('|\xa0"second"\xa0|\xa0\xa0\xa012345\xa0\xa0\xa0\xa0|')

    # Verify steps for second scenario
    given_step_2 = mock_client.start_test_item.call_args_list[5]
    assert given_step_2[0][0] == "Given It is test with parameters"
    assert given_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert given_step_2[1]["has_stats"] is False

    when_step_2 = mock_client.start_test_item.call_args_list[6]
    assert when_step_2[0][0] == 'When I have parameter "second"'
    assert when_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert when_step_2[1]["has_stats"] is False

    then_step_2 = mock_client.start_test_item.call_args_list[7]
    assert then_step_2[0][0] == "Then I emit number 12345 on level info"
    assert then_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert then_step_2[1]["has_stats"] is False

    # Verify third scenario with parameters
    scenario_call_3 = mock_client.start_test_item.call_args_list[8]
    assert (
        scenario_call_3[1]["name"]
        == "Feature: Basic test with parameters - Scenario Outline: Test with different parameters"
    )
    assert scenario_call_3[1]["item_type"] == "STEP"
    assert scenario_call_3[1].get("has_stats", True)
    assert (
        scenario_call_3[1]["code_ref"]
        == "features/scenario_outline_parameters.feature/[EXAMPLE:Test with different parameters"
        '[parameters:12345678;str:"third"]]'
    )
    parameters = scenario_call_3[1]["parameters"].items()
    assert len(parameters) == 2
    assert ("str", '"third"') in parameters
    assert ("parameters", "12345678") in parameters
    assert scenario_call_3[1]["description"] is not None
    assert scenario_call_3[1]["description"].endswith('|\xa0"third"\xa0|\xa0\xa012345678\xa0\xa0|')

    # Verify steps for third scenario
    given_step_3 = mock_client.start_test_item.call_args_list[9]
    assert given_step_3[0][0] == "Given It is test with parameters"
    assert given_step_3[1]["parent_item_id"] == scenario_call_3[1]["name"] + "_3"
    assert given_step_3[1]["has_stats"] is False

    when_step_3 = mock_client.start_test_item.call_args_list[10]
    assert when_step_3[0][0] == 'When I have parameter "third"'
    assert when_step_3[1]["parent_item_id"] == scenario_call_3[1]["name"] + "_3"
    assert when_step_3[1]["has_stats"] is False

    then_step_3 = mock_client.start_test_item.call_args_list[11]
    assert then_step_3[0][0] == "Then I emit number 12345678 on level info"
    assert then_step_3[1]["parent_item_id"] == scenario_call_3[1]["name"] + "_3"
    assert then_step_3[1]["has_stats"] is False

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_examples_tags(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/example_tags_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario
    scenario_call = mock_client.start_test_item.call_args_list[0]
    scenario_attrs = scenario_call[1].get("attributes", None)
    assert scenario_attrs is not None
    assert len(scenario_attrs) == 1
    assert {"value": "test"} in scenario_attrs

    # Verify second scenario
    scenario_call = mock_client.start_test_item.call_args_list[4]
    scenario_attrs = scenario_call[1].get("attributes", None)
    assert scenario_attrs is not None
    assert len(scenario_attrs) == 1
    assert {"value": "test"} in scenario_attrs

    # Verify third scenario
    scenario_call = mock_client.start_test_item.call_args_list[8]
    scenario_attrs = scenario_call[1].get("attributes", None)
    assert scenario_attrs is not None
    assert len(scenario_attrs) == 1
    assert {"value": "test"} in scenario_attrs

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_background_steps(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_background_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario with background
    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call_1[1]["name"]
        == "Feature: Basic test with parameters and background - Scenario Outline: Test with different parameters"
    )
    assert scenario_call_1[1]["item_type"] == "STEP"
    assert scenario_call_1[1].get("has_stats", True)
    assert (
        scenario_call_1[1]["code_ref"]
        == "features/scenario_outline_background.feature/[EXAMPLE:Test with different parameters"
        '[parameters:123;str:"first"]]'
    )
    parameters = scenario_call_1[1]["parameters"].items()
    assert len(parameters) == 2
    assert ("str", '"first"') in parameters
    assert ("parameters", "123") in parameters

    # Verify the Background step
    background_call = mock_client.start_test_item.call_args_list[1]
    assert background_call[0][0] == "Background"
    assert background_call[0][2] == "step"
    assert background_call[1]["has_stats"] is False
    assert background_call[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"

    # Verify background step for first scenario
    background_step_1 = mock_client.start_test_item.call_args_list[2]
    assert background_step_1[0][0] == "Given I have empty step in background"
    assert background_step_1[1]["parent_item_id"] == background_call[0][0] + "_4"
    assert background_step_1[1]["has_stats"] is False

    # Verify regular steps for first scenario
    given_step_1 = mock_client.start_test_item.call_args_list[3]
    assert given_step_1[0][0] == "Given It is test with parameters"
    assert given_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert given_step_1[1]["has_stats"] is False

    when_step_1 = mock_client.start_test_item.call_args_list[4]
    assert when_step_1[0][0] == 'When I have parameter "first"'
    assert when_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert when_step_1[1]["has_stats"] is False

    then_step_1 = mock_client.start_test_item.call_args_list[5]
    assert then_step_1[0][0] == "Then I emit number 123 on level info"
    assert then_step_1[1]["parent_item_id"] == scenario_call_1[1]["name"] + "_1"
    assert then_step_1[1]["has_stats"] is False

    # Verify second scenario with background
    scenario_call_2 = mock_client.start_test_item.call_args_list[6]
    assert (
        scenario_call_2[1]["name"]
        == "Feature: Basic test with parameters and background - Scenario Outline: Test with different parameters"
    )
    assert scenario_call_2[1]["item_type"] == "STEP"
    assert scenario_call_2[1].get("has_stats", True)
    assert (
        scenario_call_2[1]["code_ref"]
        == "features/scenario_outline_background.feature/[EXAMPLE:Test with different parameters"
        '[parameters:12345;str:"second"]]'
    )
    parameters = scenario_call_2[1]["parameters"].items()
    assert len(parameters) == 2
    assert ("str", '"second"') in parameters
    assert ("parameters", "12345") in parameters

    # Verify the Background step
    background_call = mock_client.start_test_item.call_args_list[7]
    assert background_call[0][0] == "Background"
    assert background_call[0][2] == "step"
    assert background_call[1]["has_stats"] is False
    assert background_call[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"

    # Verify background step for second scenario
    background_step_2 = mock_client.start_test_item.call_args_list[8]
    assert background_step_2[0][0] == "Given I have empty step in background"
    assert background_step_2[1]["parent_item_id"] == background_call[0][0] + "_5"
    assert background_step_2[1]["has_stats"] is False

    # Verify steps for second scenario
    given_step_2 = mock_client.start_test_item.call_args_list[9]
    assert given_step_2[0][0] == "Given It is test with parameters"
    assert given_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert given_step_2[1]["has_stats"] is False

    when_step_2 = mock_client.start_test_item.call_args_list[10]
    assert when_step_2[0][0] == 'When I have parameter "second"'
    assert when_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert when_step_2[1]["has_stats"] is False

    then_step_2 = mock_client.start_test_item.call_args_list[11]
    assert then_step_2[0][0] == "Then I emit number 12345 on level info"
    assert then_step_2[1]["parent_item_id"] == scenario_call_2[1]["name"] + "_2"
    assert then_step_2[1]["has_stats"] is False

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_description(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_description_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario with description
    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    description_1 = scenario_call_1[1]["description"]
    assert description_1.startswith("The description for the scenario outline")
    assert "Parameters:\n\n" in description_1
    assert "|\xa0\xa0\xa0str\xa0\xa0\xa0|\xa0parameters\xa0|" in description_1
    assert '|\xa0"first"\xa0|\xa0\xa0\xa0\xa0123\xa0\xa0\xa0\xa0\xa0|' in description_1

    scenario_call_2 = mock_client.start_test_item.call_args_list[4]
    description_2 = scenario_call_2[1]["description"]
    assert description_2.startswith("The description for the scenario outline")
    assert "Parameters:\n\n" in description_2
    assert "|\xa0\xa0\xa0str\xa0\xa0\xa0\xa0|\xa0parameters\xa0|" in description_2
    assert '|\xa0"second"\xa0|\xa0\xa0\xa012345\xa0\xa0\xa0\xa0|' in description_2

    # Verify the steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_rule_description(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    variables = {"rp_hierarchy_code": True}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=["examples/bdd/step_defs/test_rule_description_steps.py"], variables=variables
    )
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify Feature call
    feature_call = mock_client.start_test_item.call_args_list[0]
    assert feature_call[1]["name"] == "Feature: Test rule keyword"
    assert feature_call[1]["code_ref"].endswith("rule_description.feature")

    # Verify Rule call
    rule_call = mock_client.start_test_item.call_args_list[1]
    assert rule_call[1]["name"] == "Rule: The first rule"
    assert rule_call[1]["description"] == "Description for the Rule"
    assert rule_call[1]["item_type"] == "SUITE"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_dynamic_name(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_name_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call_1[1]["name"]
        == 'Feature: Dynamic scenario outline names - Scenario Outline: Test with the parameter "first"'
    )
    assert scenario_call_1[1]["item_type"] == "STEP"
    assert (
        scenario_call_1[1]["code_ref"] == "features/dynamic_scenario_outline_names.feature/"
        '[EXAMPLE:Test with the parameter "first"[parameters:123;str:"first"]]'
    )
    assert scenario_call_1[1]["parameters"] == {"str": '"first"', "parameters": "123"}
    assert scenario_call_1[1]["description"] == (
        "Parameters:\n\n"
        "\xa0\xa0\xa0\xa0|\xa0\xa0\xa0str\xa0\xa0\xa0|\xa0parameters\xa0|\n"
        "\xa0\xa0\xa0\xa0|---------|------------|\n"
        '\xa0\xa0\xa0\xa0|\xa0"first"\xa0|\xa0\xa0\xa0\xa0123\xa0\xa0\xa0\xa0\xa0|'
    )

    scenario_call_2 = mock_client.start_test_item.call_args_list[4]
    assert (
        scenario_call_2[1]["name"]
        == 'Feature: Dynamic scenario outline names - Scenario Outline: Test with the parameter "second"'
    )
    assert scenario_call_2[1]["item_type"] == "STEP"
    assert (
        scenario_call_2[1]["code_ref"] == "features/dynamic_scenario_outline_names.feature/"
        '[EXAMPLE:Test with the parameter "second"[parameters:12345;str:"second"]]'
    )
    assert scenario_call_2[1]["parameters"] == {"str": '"second"', "parameters": "12345"}
    assert scenario_call_2[1]["description"] == (
        "Parameters:\n\n"
        "\xa0\xa0\xa0\xa0|\xa0\xa0\xa0str\xa0\xa0\xa0\xa0|\xa0parameters\xa0|\n"
        "\xa0\xa0\xa0\xa0|----------|------------|\n"
        '\xa0\xa0\xa0\xa0|\xa0"second"\xa0|\xa0\xa0\xa012345\xa0\xa0\xa0\xa0|'
    )


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_fail(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_fail_steps.py"])
    assert int(result) == 1, "Exit code should be 1 (test error)"

    # Verify first scenario with parameters
    scenario_call_1 = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call_1[1]["name"]
        == "Feature: Basic test with parameters which fails - Scenario Outline: Test with different parameters failing"
    )
    assert scenario_call_1[1]["item_type"] == "STEP"
    assert scenario_call_1[1].get("has_stats", True)
    assert (
        scenario_call_1[1]["code_ref"]
        == "features/scenario_outline_fail.feature/[EXAMPLE:Test with different parameters failing"
        '[parameters:123;str:"first"]]'
    )

    # Check failure logging for first scenario
    finish_step_call_1 = mock_client.finish_test_item.call_args_list[3]
    assert finish_step_call_1[1]["status"] == "FAILED"
    assert finish_step_call_1[0][0].startswith("Then I fail")

    finish_scenario_call_1 = mock_client.finish_test_item.call_args_list[4]
    assert finish_scenario_call_1[1]["status"] == "FAILED"
    assert finish_scenario_call_1[1]["item_id"] == scenario_call_1[1]["name"] + "_1"

    log_calls = [
        log_call
        for log_call in mock_client.log.call_args_list
        if "level" in log_call[1] and log_call[1]["level"] == "ERROR"
    ]
    assert len(log_calls) >= 2, "Should have at least 2 error log calls"

    error_log = log_calls[0][1]
    assert "AssertionError: This step always fails" in error_log["message"]
    assert error_log["item_id"].startswith("Then I fail")

    final_error_log = log_calls[1][1]
    assert final_error_log["level"] == "ERROR"
    assert final_error_log["message"].endswith("AssertionError")
    assert final_error_log["item_id"] == scenario_call_1[1]["name"] + "_1"

    # Verify first scenario with parameters
    scenario_call_2 = mock_client.start_test_item.call_args_list[5]
    assert (
        scenario_call_2[1]["name"]
        == "Feature: Basic test with parameters which fails - Scenario Outline: Test with different parameters failing"
    )
    assert scenario_call_2[1]["item_type"] == "STEP"
    assert scenario_call_2[1].get("has_stats", True)
    assert (
        scenario_call_2[1]["code_ref"]
        == "features/scenario_outline_fail.feature/[EXAMPLE:Test with different parameters failing"
        '[parameters:12345;str:"second"]]'
    )

    # Check failure logging for first scenario
    finish_step_call_2 = mock_client.finish_test_item.call_args_list[5 + 3]
    assert finish_step_call_2[1]["status"] == "FAILED"
    assert finish_step_call_2[0][0].startswith("Then I fail")

    finish_scenario_call_2 = mock_client.finish_test_item.call_args_list[5 + 4]
    assert finish_scenario_call_2[1]["status"] == "FAILED"
    assert finish_scenario_call_2[1]["item_id"] == scenario_call_2[1]["name"] + "_2"

    error_log = log_calls[2][1]
    assert "AssertionError: This step always fails" in error_log["message"]
    assert error_log["item_id"].startswith("Then I fail")

    final_error_log = log_calls[3][1]
    assert final_error_log["level"] == "ERROR"
    assert final_error_log["message"].endswith("AssertionError")
    assert final_error_log["item_id"] == scenario_call_1[1]["name"] + "_2"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_doc_string_parameters(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/doc_string_parameters_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify scenario
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call[1]["name"]
        == "Feature: Basic test with a docstring parameter - Scenario: Test with a docstring parameter"
    )
    assert scenario_call[1]["item_type"] == "STEP"
    assert scenario_call[1].get("has_stats", True)
    assert (
        scenario_call[1]["code_ref"]
        == "features/doc_string_parameters.feature/[SCENARIO:Test with a docstring parameter]"
    )

    # Verify step
    given_step = mock_client.start_test_item.call_args_list[1]
    assert given_step[0][0] == "Given I have a docstring parameter:"
    assert given_step[0][2] == "step"
    assert given_step[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"
    assert given_step[1]["has_stats"] is False

    # Verify steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@mock.patch(REPORT_PORTAL_SERVICE)
def test_data_table_parameter_steps(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/data_table_parameter_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify scenario
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call[1]["name"]
        == "Feature: A basic test with a Data Table parameter - Scenario: Test with Data Table"
    )
    assert scenario_call[1]["item_type"] == "STEP"
    assert scenario_call[1].get("has_stats", True)
    assert scenario_call[1]["code_ref"] == "features/data_table_parameter.feature/[SCENARIO:Test with Data Table]"

    # Verify step
    given_step = mock_client.start_test_item.call_args_list[1]
    assert given_step[0][0] == "Given a step with a data table:"
    assert given_step[0][2] == "step"
    assert given_step[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"
    assert given_step[1]["has_stats"] is False

    # Verify steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_scenario_outline_test_case_id(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/scenario_outline_test_case_id_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify first scenario with parameters includes the test case ID
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert (
        scenario_call[1]["name"]
        == "Feature: Basic test with parameters - Scenario Outline: Test with different parameters"
    )
    assert scenario_call[1]["item_type"] == "STEP"
    assert (
        scenario_call[1]["code_ref"]
        == "features/scenario_outline_test_case_id.feature/[EXAMPLE:Test with different parameters"
        '[parameters:123;str:"first"]]'
    )
    assert scenario_call[1]["parameters"] == {"str": '"first"', "parameters": "123"}

    # Verify the test case ID is correctly reported using the tag instead of code_ref
    assert scenario_call[1]["test_case_id"] == 'outline_tc_id[parameters:123;str:"first"]'

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_custom_test_case_id(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/custom_test_case_id_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify scenario includes the test case ID
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["name"] == "Feature: Test dummy scenario - Scenario: The scenario"
    assert scenario_call[1]["item_type"] == "STEP"
    assert scenario_call[1]["code_ref"] == "features/custom_test_case_id.feature/[SCENARIO:The scenario]"

    # Verify the test case ID is correctly reported using the tag instead of code_ref
    assert scenario_call[1]["test_case_id"] == "my_tc_id"

    # Verify step info
    step_call = mock_client.start_test_item.call_args_list[1]
    assert step_call[0][0] == "Given I have empty step"
    assert step_call[0][2] == "step"
    assert step_call[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"
    assert step_call[1]["has_stats"] is False

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_tests_attributes_rule(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    variables = {"rp_tests_attributes": "test_key:test_value"}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=["examples/bdd/step_defs/test_rule_description_steps.py"], variables=variables
    )
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["attributes"] == [{"key": "test_key", "value": "test_value"}]


@pytest.mark.skipif(pytest_bdd_version[0] < 8, reason="Only for pytest-bdd 8+")
@pytest.mark.parametrize("rp_hierarchy_code, scenario_idx", [(True, 2), (False, 0)])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_tests_attributes_rule_hierarchy(mock_client_init, rp_hierarchy_code, scenario_idx):
    mock_client = setup_mock(mock_client_init)
    variables = {"rp_tests_attributes": "test_key:test_value", "rp_hierarchy_code": rp_hierarchy_code}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=["examples/bdd/step_defs/test_rule_description_steps.py"], variables=variables
    )
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    scenario_call = mock_client.start_test_item.call_args_list[scenario_idx]
    assert scenario_call[1]["attributes"] == [{"key": "test_key", "value": "test_value"}]


@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_tests_attributes_bdd_tags(mock_client_init):
    mock_client = setup_mock(mock_client_init)
    variables = {"rp_tests_attributes": "test_key:test_value"}
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/test_belly.py"], variables=variables)
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    scenario_call = mock_client.start_test_item.call_args_list[0]
    attributes = scenario_call[1]["attributes"]
    assert len(attributes) == 3
    assert {"key": "test_key", "value": "test_value"} in attributes
    assert {"value": "ok"} in attributes
    assert {"key": "key", "value": "value"} in attributes


@mock.patch(REPORT_PORTAL_SERVICE)
def test_long_step(mock_client_init):
    mock_client = setup_mock_for_logging(mock_client_init)
    result = utils.run_pytest_tests(tests=["examples/bdd/step_defs/long_step_scenario_steps.py"])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    # Verify scenario is correctly identified
    scenario_call = mock_client.start_test_item.call_args_list[0]
    assert scenario_call[1]["name"] == "Feature: Test long step scenario - Scenario: The scenario"
    assert scenario_call[1]["item_type"] == "STEP"
    assert scenario_call[1]["code_ref"] == "features/long_step_scenario.feature/[SCENARIO:The scenario]"

    # Verify step is truncated but still identifiable
    step_call = mock_client.start_test_item.call_args_list[1]
    step_name = step_call[0][0]
    assert step_name.startswith("Given A very long step.")
    assert len(step_name) <= 1024, "Step name should be truncated to at most 1024 characters"
    assert step_name.endswith("..."), "Truncated step should have ellipsis"

    # Verify step details
    assert step_call[0][2] == "step"
    assert step_call[1]["parent_item_id"] == scenario_call[1]["name"] + "_1"
    assert step_call[1]["has_stats"] is False

    # Verify all steps pass
    finish_calls = mock_client.finish_test_item.call_args_list
    for call in finish_calls:
        assert call[1]["status"] == "PASSED"
