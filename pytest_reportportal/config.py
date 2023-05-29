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
        self.rp_rerun = (getenv('RP_RERUN') or pytest_config.option.rp_rerun or
                         pytest_config.getini('rp_rerun'))
        self.rp_endpoint = getenv('RP_ENDPOINT') or self.find_option(pytest_config, 'rp_endpoint')
        self.rp_hierarchy_code = getenv('RP_HIERARCHY_CODE') or self.find_option(pytest_config,
                                                                                 'rp_hierarchy_code')
        self.rp_dir_level = int(getenv('RP_HIERARCHY_DIRS_LEVEL') or self.find_option(pytest_config,
                                                                                      'rp_hierarchy_dirs_level'))
        self.rp_hierarchy_dirs = getenv('RP_HIERARCHY_DIRS') or self.find_option(pytest_config,
                                                                                 'rp_hierarchy_dirs')
        self.rp_dir_path_separator = \
            getenv('RP_HIERARCHY_DIR_PATH_SEPARATOR') or self.find_option(pytest_config,
                                                                          'rp_hierarchy_dir_path_separator')
        ignore_attributes = getenv('RP_IGNORE_ATTRIBUTES') or self.find_option(pytest_config,
                                                                               'rp_ignore_attributes')
        self.rp_ignore_attributes = set(ignore_attributes) \
            if ignore_attributes else set()
        self.rp_is_skipped_an_issue = getenv('RP_IS_SKIPPED_AN_ISSUE') or self.find_option(
            pytest_config,
            'rp_is_skipped_an_issue'
        )
        self.rp_issue_id_marks = getenv('RP_ISSUE_ID_MARKS') or self.find_option(pytest_config,
                                                                                 'rp_issue_id_marks')
        self.rp_issue_system_url = getenv('RP_ISSUE_SYSTEM_URL') or self.find_option(pytest_config,
                                                                                     'rp_issue_system_url')
        self.rp_bts_project = getenv('RP_BTS_PROJECT') or self.find_option(pytest_config, 'rp_bts_project')
        self.rp_bts_url = getenv('RP_BTS_URL') or self.find_option(pytest_config, 'rp_bts_url')
        self.rp_launch = getenv('RP_LAUNCH') or self.find_option(pytest_config, 'rp_launch')
        self.rp_launch_id = getenv('RP_LAUNCH_ID') or self.find_option(pytest_config, 'rp_launch_id')
        self.rp_launch_attributes = getenv('RP_LAUNCH_ATTRIBUTES') or self.find_option(pytest_config,
                                                                                       'rp_launch_attributes')
        self.rp_launch_description = getenv('RP_LAUNCH_DESCRIPTION') or self.find_option(pytest_config,
                                                                                         'rp_launch_description')
        self.rp_log_batch_size = int(getenv('RP_LOG_BATCH_SIZE') or self.find_option(pytest_config,
                                                                                     'rp_log_batch_size'))
        batch_payload_size = getenv('RP_LOG_BATCH_PAYLOAD_SIZE') or self.find_option(
            pytest_config, 'rp_log_batch_payload_size')
        if batch_payload_size:
            self.rp_log_batch_payload_size = int(batch_payload_size)
        else:
            self.rp_log_batch_payload_size = MAX_LOG_BATCH_PAYLOAD_SIZE
        self.rp_log_level = getenv('RP_LOG_LEVEL') or get_actual_log_level(pytest_config, 'rp_log_level')
        self.rp_log_format = getenv('RP_LOG_FORMAT') or self.find_option(pytest_config, 'rp_log_format')
        self.rp_thread_logging = bool(strtobool(str(getenv('RP_THREAD_LOGGING') or self.find_option(
            pytest_config, 'rp_thread_logging'
        ) or False)))
        self.rp_mode = getenv('RP_MODE') or self.find_option(pytest_config, 'rp_mode')
        self.rp_parent_item_id = getenv('RP_PARENT_ITEM_ID') or self.find_option(pytest_config,
                                                                                 'rp_parent_item_id')
        self.rp_project = getenv('RP_PROJECT') or self.find_option(pytest_config,
                                                                   'rp_project')
        self.rp_rerun_of = getenv('RP_RERUN_OF') or self.find_option(pytest_config,
                                                                     'rp_rerun_of')
        self.rp_retries = int(getenv('RP_RETRIES') or self.find_option(pytest_config,
                                                                       'retries'))
        self.rp_skip_connection_test = str(
            getenv('RP_SKIP_CONNECTION_TEST') or self.find_option(pytest_config,
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
