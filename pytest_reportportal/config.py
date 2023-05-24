"""This module contains class that stores RP agent configuration data."""

from distutils.util import strtobool
from os import getenv

from reportportal_client.logs.log_manager import MAX_LOG_BATCH_PAYLOAD_SIZE

try:
    # This try/except can go away once we support pytest >= 5.4.0
    from _pytest.logging import get_actual_log_level
except ImportError:
    from _pytest.logging import get_log_level_for_setting as \
        get_actual_log_level


class AgentConfig(object):
    """Storage for the RP agent initialization attributes."""

    def __init__(self, pytest_config):
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
        ignore_attributes = self.find_option(pytest_config,
                                             'rp_ignore_attributes')
        self.rp_ignore_attributes = set(ignore_attributes) \
            if ignore_attributes else set()
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
        self.rp_retries = int(self.find_option(pytest_config,
                                               'retries'))
        self.rp_skip_connection_test = str(
            self.find_option(pytest_config,
                             'rp_skip_connection_test')).lower() in (
                                           'true', '1', 'yes', 'y')
        self.rp_uuid = getenv('RP_UUID') or self.find_option(pytest_config,
                                                             'rp_uuid')
        rp_verify_ssl = self.find_option(pytest_config, 'rp_verify_ssl', True)
        try:
            self.rp_verify_ssl = bool(strtobool(rp_verify_ssl))
        except (ValueError, AttributeError):
            self.rp_verify_ssl = rp_verify_ssl
        self.rp_launch_timeout = int(
            self.find_option(pytest_config, 'rp_launch_timeout'))

    # noinspection PyMethodMayBeStatic
    def find_option(self, pytest_config, option_name, default=None):
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
        return value if value else default
