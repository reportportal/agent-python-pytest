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

from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
def test_connection_close(mock_client_init):
    mock_client = mock_client_init.return_value

    result = utils.run_tests_with_client(mock_client, ["examples/test_rp_logging.py"])

    assert int(result) == 0, "Exit code should be 0 (no errors)"
    assert mock_client.close.call_count == 1, '"close" method was not called at the end of the test'
