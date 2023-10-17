#  Copyright (c) 2023 EPAM Systems
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

"""This module contains class that stores RP agent configuration data."""

import warnings
from distutils.util import strtobool
from os import getenv
from typing import Optional, Union, Any, Tuple

from _pytest.config import Config
from reportportal_client import OutputType, ClientType
from reportportal_client.logs import MAX_LOG_BATCH_PAYLOAD_SIZE

try:
    # This try/except can go away once we support pytest >= 5.4.0
    from _pytest.logging import get_actual_log_level
except ImportError:
    from _pytest.logging import get_log_level_for_setting as \
        get_actual_log_level


class AgentConfig:
    """Storage for the RP agent initialization attributes."""

    rp_client_type: Optional[ClientType]
    rp_rerun: Optional[bool]
    pconfig: Config
    rp_endpoint: str
    rp_hierarchy_code: bool
    rp_dir_level: int
    rp_hierarchy_dirs: bool
    rp_dir_path_separator: str
    rp_ignore_attributes: set
    rp_is_skipped_an_issue: bool
    rp_issue_id_marks: bool
    rp_issue_system_url: str
    rp_bts_project: str
    rp_bts_url: str
    rp_launch: str
    rp_launch_id: Optional[str]
    rp_launch_attributes: Optional[list]
    rp_launch_description: str
    rp_log_batch_size: int
    rp_log_batch_payload_size: int
    rp_log_level: Optional[int]
    rp_log_format: Optional[str]
    rp_mode: str
    rp_parent_item_id: Optional[str]
    rp_project: str
    rp_rerun_of: Optional[str]
    rp_api_retries: int
    rp_skip_connection_test: bool
    rp_api_key: str
    rp_verify_ssl: Union[bool, str]
    rp_launch_timeout: int
    rp_launch_uuid_print: bool
    rp_launch_uuid_print_output: Optional[OutputType]
    rp_http_timeout: Optional[Union[Tuple[float, float], float]]

    def __init__(self, pytest_config: Config) -> None:
        """Initialize required attributes."""
        self.rp_rerun = (pytest_config.option.rp_rerun or
                         pytest_config.getini('rp_rerun'))
        self.rp_endpoint = self.find_option(pytest_config, 'rp_endpoint')
        self.rp_hierarchy_code = self.find_option(pytest_config,
                                                  'rp_hierarchy_code')
        self.rp_dir_level = int(self.find_option(pytest_config,
                                                 'rp_hierarchy_dirs_level'))
        self.rp_hierarchy_dirs = self.find_option(pytest_config,
                                                  'rp_hierarchy_dirs')
        self.rp_dir_path_separator = \
            self.find_option(pytest_config, 'rp_hierarchy_dir_path_separator')
        self.rp_ignore_attributes = set(self.find_option(pytest_config, 'rp_ignore_attributes') or [])
        self.rp_is_skipped_an_issue = self.find_option(
            pytest_config,
            'rp_is_skipped_an_issue'
        )
        self.rp_issue_id_marks = self.find_option(pytest_config,
                                                  'rp_issue_id_marks')
        self.rp_issue_system_url = self.find_option(pytest_config,
                                                    'rp_issue_system_url')
        self.rp_bts_project = self.find_option(pytest_config, 'rp_bts_project')
        self.rp_bts_url = self.find_option(pytest_config, 'rp_bts_url')
        self.rp_launch = self.find_option(pytest_config, 'rp_launch')
        self.rp_launch_id = self.find_option(pytest_config, 'rp_launch_id')
        self.rp_launch_attributes = self.find_option(pytest_config,
                                                     'rp_launch_attributes')
        self.rp_launch_description = self.find_option(pytest_config,
                                                      'rp_launch_description')
        self.rp_log_batch_size = int(self.find_option(pytest_config,
                                                      'rp_log_batch_size'))
        batch_payload_size = self.find_option(
            pytest_config, 'rp_log_batch_payload_size')
        if batch_payload_size:
            self.rp_log_batch_payload_size = int(batch_payload_size)
        else:
            self.rp_log_batch_payload_size = MAX_LOG_BATCH_PAYLOAD_SIZE
        self.rp_log_level = get_actual_log_level(pytest_config, 'rp_log_level')
        self.rp_log_format = self.find_option(pytest_config, 'rp_log_format')
        self.rp_thread_logging = bool(strtobool(str(self.find_option(
            pytest_config, 'rp_thread_logging'
        ) or False)))
        self.rp_mode = self.find_option(pytest_config, 'rp_mode')
        self.rp_parent_item_id = self.find_option(pytest_config,
                                                  'rp_parent_item_id')
        self.rp_project = self.find_option(pytest_config,
                                           'rp_project')
        self.rp_rerun_of = self.find_option(pytest_config,
                                            'rp_rerun_of')
        self.rp_skip_connection_test = str(
            self.find_option(pytest_config,
                             'rp_skip_connection_test')).lower() in (
                                           'true', '1', 'yes', 'y')

        rp_api_retries_str = self.find_option(pytest_config, 'rp_api_retries')
        rp_api_retries = rp_api_retries_str and int(rp_api_retries_str)
        if rp_api_retries and rp_api_retries > 0:
            self.rp_api_retries = rp_api_retries
        else:
            rp_api_retries_str = self.find_option(pytest_config, 'retries')
            rp_api_retries = rp_api_retries_str and int(rp_api_retries_str)
            if rp_api_retries and rp_api_retries > 0:
                self.rp_api_retries = rp_api_retries
                warnings.warn(
                    'Parameter `retries` is deprecated since 5.1.9 '
                    'and will be subject for removing in the next '
                    'major version. Use `rp_api_retries` argument '
                    'instead.',
                    DeprecationWarning,
                    2
                )
            else:
                self.rp_api_retries = 0

        self.rp_api_key = getenv(
            'RP_API_KEY') or self.find_option(pytest_config, 'rp_api_key')
        if not self.rp_api_key:
            self.rp_api_key = getenv(
                'RP_UUID') or self.find_option(pytest_config, 'rp_uuid')
            if self.rp_api_key:
                warnings.warn(
                    'Parameter `rp_uuid` is deprecated since 5.1.9 '
                    'and will be subject for removing in the next '
                    'major version. Use `rp_api_key` argument '
                    'instead.',
                    DeprecationWarning,
                    2
                )
            else:
                warnings.warn(
                    'Argument `rp_api_key` is `None` or empty string, '
                    'that is not supposed to happen because Report '
                    'Portal is usually requires an authorization key. '
                    'Please check your configuration.',
                    RuntimeWarning,
                    2
                )

        rp_verify_ssl = self.find_option(pytest_config, 'rp_verify_ssl', True)
        try:
            self.rp_verify_ssl = bool(strtobool(rp_verify_ssl))
        except (ValueError, AttributeError):
            self.rp_verify_ssl = rp_verify_ssl
        self.rp_launch_timeout = int(
            self.find_option(pytest_config, 'rp_launch_timeout'))

        self.rp_launch_uuid_print = bool(strtobool(self.find_option(
            pytest_config, 'rp_launch_uuid_print'
        ) or 'False'))
        print_output = self.find_option(pytest_config, 'rp_launch_uuid_print_output')
        self.rp_launch_uuid_print_output = OutputType[print_output.upper()] if print_output else None
        client_type = self.find_option(pytest_config, 'rp_client_type')
        self.rp_client_type = ClientType[client_type.upper()] if client_type else ClientType.SYNC

        connect_timeout = self.find_option(pytest_config, 'rp_connect_timeout')
        connect_timeout = float(connect_timeout) if connect_timeout else None
        read_timeout = self.find_option(pytest_config, 'rp_read_timeout')
        read_timeout = float(read_timeout) if read_timeout else None
        if connect_timeout is None and read_timeout is None:
            self.rp_http_timeout = None
        elif connect_timeout is not None and read_timeout is not None:
            self.rp_http_timeout = (connect_timeout, read_timeout)
        else:
            self.rp_http_timeout = connect_timeout or read_timeout

    # noinspection PyMethodMayBeStatic
    def find_option(self, pytest_config: Config, option_name: str, default: Any = None) -> Any:
        """
        Find a single configuration setting from multiple places.

        The value is retrieved in the following places in priority order:

        1. From `self.pconfig.option.[option_name]`.
        2. From `self.pconfig.getini(option_name)`.

        :param pytest_config: config object of PyTest
        :param option_name:   name of the option
        :param default:       value to be returned if not found
        :return: option value
        """
        value = (
                getattr(pytest_config.option, option_name, None) or
                pytest_config.getini(option_name)
        )
        if isinstance(value, bool):
            return value
        return value or default
