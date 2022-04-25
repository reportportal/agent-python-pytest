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
from pytest_reportportal.config import AgentConfig


@pytest.mark.parametrize(
    ['verify_ssl', 'expected_result'],
    [
        ('True', True),
        ('False', False),
        ('true', True),
        ('false', False),
        (True, True),
        (False, False),
        ('path/to/certificate', 'path/to/certificate'),
        (None, True)
    ]
)
def test_verify_ssl_true(mocked_config, verify_ssl, expected_result):
    mocked_config.getini.side_effect = \
        lambda x: verify_ssl if x == 'rp_verify_ssl' else None
    config = AgentConfig(mocked_config)

    assert config.rp_verify_ssl == expected_result
