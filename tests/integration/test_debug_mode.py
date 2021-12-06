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

from six.moves import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
def test_launch_mode(mock_client_init):
    variables = {'RP_MODE': 'DEBUG'}
    for k, v in utils.DEFAULT_VARIABLES.items():
        variables[k] = v

    result = utils.run_pytest_tests(tests=['examples/test_simple.py'],
                                    variables=variables)
    assert result.value == 0
