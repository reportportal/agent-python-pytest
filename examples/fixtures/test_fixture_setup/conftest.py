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

import logging
from unittest import mock

import pytest
from reportportal_client import RPLogger

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
logging.setLoggerClass(RPLogger)

LOG_MESSAGE_SETUP = 'Log message for setup'


@pytest.fixture
def fixture_setup_config():
    logging.error(LOG_MESSAGE_SETUP)
    return mock.Mock()
