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

"""This module includes integration tests for Test Case ID report with use_index parameter."""

from unittest import mock

import pytest

from examples.test_case_id import (
    test_case_id_decorator_use_index_false,
    test_case_id_decorator_use_index_partial_params,
    test_case_id_decorator_use_index_true,
)
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize(
    ["test", "expected_id"],
    [
        # Test use_index=True: should use parameter indices instead of values
        # Format should be: ('param1', 0),('param2', 0) instead of value1,value2
        (
            "examples/test_case_id/test_case_id_decorator_use_index_true.py",
            test_case_id_decorator_use_index_true.TEST_CASE_ID + "[('param1', 0),('param2', 0)]",
        ),
        # Test use_index=False: should use parameter values (default behavior)
        (
            "examples/test_case_id/test_case_id_decorator_use_index_false.py",
            test_case_id_decorator_use_index_false.TEST_CASE_ID + "[value1,value2]",
        ),
        # Test use_index=True with selected params: should use index for selected param only
        # Should be ('param1', 0) instead of value1
        (
            "examples/test_case_id/test_case_id_decorator_use_index_partial_params.py",
            test_case_id_decorator_use_index_partial_params.TEST_CASE_ID + "[('param1', 0)]",
        ),
    ],
)
def test_use_index_parameters(mock_client_init, test, expected_id):
    """Verify the use_index parameter in Test Case ID functionality.

    This test verifies that the new use_index parameter works correctly for parameterized tests.
    When use_index=True, the test case ID should include parameter indices instead of parameter values.
    This is useful for scenarios where parameter values might change between test runs but the indices
    remain constant, ensuring that retry groups are properly maintained.

    The test covers:
    1. use_index=True with all parameters - should use (param_name, index) format
    2. use_index=False - should use parameter values (default behavior)
    3. use_index=True with selected parameters - should use indices only for selected params

    :param mock_client_init: Pytest fixture for mocking the ReportPortal client
    :param test:         a test file path to run
    :param expected_id:  the expected Test Case ID format
    """
    result = utils.run_pytest_tests(tests=[test])
    assert int(result) == 0, "Exit code should be 0 (no errors)"

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    assert step_call_args["test_case_id"] == expected_id
