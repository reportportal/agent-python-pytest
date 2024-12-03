#  Copyright 2024 EPAM Systems
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

import pytest

from custom_name.test_custom_name_args import TEST_NAME_ARGS
from custom_name.test_custom_name_empty import TEST_NAME_EMPTY
from custom_name.test_custom_name_kwargs import TEST_NAME_KWARGS
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@pytest.mark.parametrize('test, expected', [
    ('examples/custom_name/test_custom_name_args.py', TEST_NAME_ARGS),
    ('examples/custom_name/test_custom_name_kwargs.py', TEST_NAME_KWARGS),
    ('examples/custom_name/test_custom_name_empty.py', TEST_NAME_EMPTY)
])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_custom_attribute_report(mock_client_init, test, expected):
    result = utils.run_pytest_tests(tests=[test], variables=utils.DEFAULT_VARIABLES)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    assert start_count == finish_count == 1, 'Incorrect number of "start_test_item" or "finish_test_item" calls'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[0][1]
    assert step_call_args['name'] == expected, 'Incorrect item name'
    assert step_call_args['attributes'] == [], 'No attributes should be added for the test item'
