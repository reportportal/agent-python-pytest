"""This module includes integration tests for different suite hierarchy."""

#  Copyright (c) 2021 http://reportportal.io .
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

import pytest
from delayed_assert import expect, assert_expectations
from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils
from tests.integration import HIERARCHY_TEST_PARAMETERS


def verify_start_item_parameters(mock_client, expected_items):
    assert mock_client.start_test_item.call_count == len(expected_items), \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    for i, call in enumerate(call_args):
        start_kwargs = call[1]
        expect(start_kwargs['name'] == expected_items[i]['name'])
        expect(start_kwargs['item_type'] == expected_items[i]['item_type'])
        verification = expected_items[i]['parent_item_id']
        expect(verification(start_kwargs['parent_item_id']))
    assert_expectations()


@pytest.mark.parametrize(('test', 'variables', 'expected_items'),
                         HIERARCHY_TEST_PARAMETERS)
@mock.patch(REPORT_PORTAL_SERVICE)
def test_rp_hierarchy_parameters(mock_client_init, test, variables,
                                 expected_items):
    """Verify suite hierarchy with `rp_hierarchy_dirs=True`.

    :param mock_client_init: Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen

    result = utils.run_pytest_tests(tests=test, variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    verify_start_item_parameters(mock_client, expected_items)
