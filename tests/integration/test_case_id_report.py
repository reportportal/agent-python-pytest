"""This module includes integration tests for Test Case ID report."""
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
from unittest import mock

from examples.test_case_id import test_case_id_decorator, \
    test_case_id_decorator_params_false, test_case_id_decorator_params_no, \
    test_case_id_decorator_params_partially, test_case_id_decorator_params_true
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize(['test', 'expected_id'], [
    ('examples/test_simple.py', 'examples/test_simple.py:test_simple'),
    ('examples/params/test_in_class_parameterized.py',
     'examples/params/test_in_class_parameterized.py:Tests.'
     'test_in_class_parameterized[param]'),
    ('examples/test_case_id/test_case_id_decorator.py',
     test_case_id_decorator.TEST_CASE_ID),
    ('examples/test_case_id/test_case_id_decorator_params_false.py',
     test_case_id_decorator_params_false.TEST_CASE_ID),
    ('examples/test_case_id/test_case_id_decorator_params_no.py',
     test_case_id_decorator_params_no.TEST_CASE_ID),
    ('examples/test_case_id/test_case_id_decorator_params_partially.py',
     test_case_id_decorator_params_partially.TEST_CASE_ID + '[value1]'),
    ('examples/test_case_id/test_case_id_decorator_params_true.py',
     test_case_id_decorator_params_true.TEST_CASE_ID + '[value1,value2]'),
    ('examples/test_case_id/test_case_id_decorator_no_id.py', ''),
    ('examples/test_case_id/test_case_id_decorator_no_id_params_false.py', ''),
    ('examples/test_case_id/test_case_id_decorator_no_id_params_true.py',
     '[value1,value2]'),
    ('examples/test_case_id/'
     'test_case_id_decorator_no_id_partial_params_true.py',
     '[value2]')
])
def test_parameters(mock_client_init, test, expected_id):
    """Verify different tests have correct Test Case IDs.

    :param mock_client_init: Pytest fixture
    :param test:         a test to run
    :param expected_id:  an expected Test Case ID
    """
    variables = utils.DEFAULT_VARIABLES
    result = utils.run_pytest_tests(tests=[test],
                                    variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    assert step_call_args['test_case_id'] == expected_id
