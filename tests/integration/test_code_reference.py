"""This module includes integration tests for code references generation."""
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
@pytest.mark.parametrize(['test', 'code_ref'], [
    ('examples/test_simple.py', 'examples/test_simple.py:test_simple'),
    ('examples/params/test_in_class_parameterized.py',
     'examples/params/test_in_class_parameterized.py:'
     'Tests.test_in_class_parameterized'),
    ('examples/hierarchy/test_in_class.py',
     'examples/hierarchy/test_in_class.py:Tests.test_in_class'),
    ('examples/hierarchy/test_in_class_in_class.py',
     'examples/hierarchy/test_in_class_in_class.py:'
     'Tests.Test.test_in_class_in_class')
])
def test_code_reference(mock_client_init, test, code_ref):
    """Verify different tests have correct code reference.

    :param mock_client_init: Pytest fixture
    :param test:             a test to run
    :param code_ref:         an expected code reference value
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
    assert step_call_args['code_ref'] == code_ref
