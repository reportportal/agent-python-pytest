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

from logging import Logger
from typing import Text, Any

import pytest

from .config import AgentConfig
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.main import Session
from reportportal_client import RPClient

log: Logger
MANDATORY_PARAMETER_MISSED_PATTERN: Text
FAILED_LAUNCH_WAIT: Text

def check_connection(agent_config: AgentConfig) -> bool: ...
def is_control(config: Config) -> bool: ...
def wait_launch(rp_client: RPClient) -> bool: ...
def pytest_configure_node(node: Any) -> None: ...
def pytest_sessionstart(session: Session) -> None: ...
def pytest_collection_finish(session: Session) -> None: ...
def pytest_sessionfinish(session: Session) -> None: ...
def pytest_configure(config: Config) -> None: ...
def pytest_runtest_protocol(item: pytest.Item) -> None: ...
def pytest_runtest_makereport(item: pytest.Item) -> None: ...
def pytest_addoption(parser: Parser) -> None: ...
