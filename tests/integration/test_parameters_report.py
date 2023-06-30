"""This module includes integration tests for parameters report."""
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

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize(['test', 'expected_params'], [
    ('examples/test_simple.py', None),
    ('examples/params/test_in_class_parameterized.py', {'param': 'param'}),
    ('examples/params/test_different_parameter_types.py',
     {'integer': 1, 'floating_point': 1.5, 'boolean': True,
      'none': None})
])
def test_parameters(mock_client_init, test, expected_params):
    """Verify different tests have correct parameters.

    :param mock_client_init: Pytest fixture
    :param test:             a test to run
    :param expected_params:  an expected parameter dictionary
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
    assert step_call_args['parameters'] == expected_params
