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

from .config import AgentConfig
from typing import List, Dict, Text, Any, Tuple, Set, Optional
from pytest import Item
from threading import Lock
from reportportal_client import RPClient

class PyTestServiceClass:

    _config: AgentConfig
    _issue_types: Dict[Text, Text]
    _tree_path: Dict[Item, List[Dict[Text, Any]]]
    _log_levels: Tuple
    _skip_analytics: Text
    _start_tracker: Set[Text]
    _process_level_lock: Lock
    _launch_id: Optional[Text]
    agent_name: Text
    agent_version: Text
    ignored_attributes: List[Text]
    log_batch_size: int
    parent_item_id: Optional[Text]
    rp: Optional[RPClient]
    project_settings: Dict[Text, Any]

    def __init__(self, agent_config: AgentConfig) -> None: ...
    def start(self) -> None: ...
