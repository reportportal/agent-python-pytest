from _pytest.config import Config as Config
from typing import List, Optional, Text, Union, Any

class AgentConfig:
    rp_rerun: Optional[bool]
    pconfig: Config
    rp_endpoint: Text
    rp_hierarchy_code: bool
    rp_dir_level: int
    rp_hierarchy_dirs: bool
    rp_dir_path_separator: Text
    rp_ignore_attributes: set
    rp_is_skipped_an_issue: bool
    rp_issue_id_marks: bool
    rp_issue_system_url: Text
    rp_bts_project: Text
    rp_bts_url: Text
    rp_launch: Text
    rp_launch_id: Optional[Text]
    rp_launch_attributes: Optional[List]
    rp_launch_description: Text
    rp_log_batch_size: int
    rp_log_batch_payload_size: int
    rp_log_level: Optional[int]
    rp_log_format: Optional[Text]
    rp_mode: Text
    rp_parent_item_id: Optional[Text]
    rp_project: Text
    rp_rerun_of: Optional[Text]
    rp_retries: int
    rp_skip_connection_test: bool
    rp_uuid: Text
    rp_verify_ssl: Union[bool, Text]
    rp_launch_timeout: int

    def __init__(self, pytest_config: Config) -> None: ...

    def find_option(self, pytest_config, param: Text,
                    default: Any = ...) -> Union[Text, bool, list]: ...
