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

"""This module includes integration tests for the debug mode switch."""

import pytest
from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize(['mode', 'expected_mode'], [('DEFAULT', 'DEFAULT'),
                                                     ('DEBUG', 'DEBUG'),
                                                     (None, 'DEFAULT')])
def test_launch_mode(mock_client_init, mode, expected_mode):
    """Verify different launch modes are passed to `start_launch` method.

    :param mock_client_init: Pytest fixture
    :param mode:             a variable to be passed to pytest
    :param expected_mode:    a value which should be passed to
    ReportPortalService
    """
    variables = dict()
    if mode is not None:
        variables['rp_mode'] = mode
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_simple.py'],
                                    variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    assert mock_client_init.call_count == 1, "client wasn't initialized"

    init_kwargs = mock_client_init.call_args_list[0][1]
    assert 'mode' in init_kwargs
    assert init_kwargs['mode'] == expected_mode
