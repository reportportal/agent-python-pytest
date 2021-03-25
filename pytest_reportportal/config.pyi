from _pytest.config import Config as Config
from typing import List, Optional, Text

class AgentConfig:
    _rp_rerun: Optional[bool] = ...
    pconfig: Config = ...
    rp_endpoint: Text = ...
    rp_ignore_errors: bool = ...
    rp_ignore_attributes: Optional[List] = ...
    rp_launch: Text = ...
    rp_launch_id: Optional[Text] = ...
    rp_launch_attributes: Optional[List] = ...
    rp_launch_description: Text = ...
    rp_log_batch_size: int = ...
    rp_log_level: Optional[int] = ...
    rp_parent_item_id: Optional[Text] = ...
    rp_project: Text = ...
    rp_rerun_of: Optional[Text] = ...
    rp_retries: int = ...
    rp_uuid: Text = ...
    rp_verify_ssl: bool = ...
    def __init__(self, pytest_config: Config) -> None: ...
    @property
    def rp_rerun(self) -> Optional[bool]: ...
