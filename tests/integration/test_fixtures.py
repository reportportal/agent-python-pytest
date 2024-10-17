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
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@pytest.mark.parametrize('switch', [True, False])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_fixture_on_off(mock_client_init, switch):
    variables = dict(utils.DEFAULT_VARIABLES)
    variables['rp_report_fixtures'] = switch
    result = utils.run_pytest_tests(tests=['examples/fixtures/test_fixture_teardown'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    start_count = mock_client.start_test_item.call_count
    finish_count = mock_client.finish_test_item.call_count
    expected_count = 3 if switch else 1
    assert start_count == finish_count == expected_count, \
        'Incorrect number of "start_test_item" or "finish_test_item" calls'
