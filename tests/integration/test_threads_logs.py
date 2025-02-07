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
def test_rp_thread_logs_reporting(mock_client_init):
    """Verify logs from threads are sent to correct items`.

    :param mock_client_init: Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_thread_client = mock_client.clone()

    def init_thread_client(*_, **__):
        from reportportal_client import set_current

        set_current(mock_thread_client)
        return mock_thread_client

    mock_client.clone.side_effect = init_thread_client
    result = utils.run_tests_with_client(mock_client, ["examples/threads/"], args=["--rp-thread-logging"])

    assert int(result) == 0, "Exit code should be 0 (no errors)"
    assert mock_client.start_launch.call_count == 1, '"start_launch" method was not called'
    assert mock_client.log.call_count == 1
    assert mock_thread_client.log.call_count == 2
