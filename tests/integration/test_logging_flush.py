"""This module includes integration test for the log flushing."""

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
from multiprocessing.pool import ThreadPool


@mock.patch(REPORT_PORTAL_SERVICE)
def test_logging_flushing(mock_client_init):
    """Verify log buffer flushes after test finish.

    :param mock_client_init: Pytest fixture
    """
    def run_test():
        return utils.run_pytest_tests(['examples/test_rp_logging.py'])

    pool = ThreadPool(processes=1)
    async_result = pool.apply_async(run_test)
    result = async_result.get()
    pool.terminate()

    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.terminate.call_count == 1, \
        '"terminate" method was not called at the end of the test'
