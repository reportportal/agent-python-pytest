"""This module contains class that stores RP agent configuration data."""

from os import getenv

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
        self._rp_rerun = None
        self.pconfig = pytest_config

        self.rp_endpoint = self.find_option('rp_endpoint')
        self.rp_hierarchy_dir_path_separator = self.find_option(
            'rp_hierarchy_dir_path_separator')
        self.rp_ignore_errors = self.find_option('rp_ignore_errors')
        self.rp_ignore_attributes = self.find_option('rp_ignore_attributes')
        self.rp_is_skipped_an_issue = self.find_option(
            'rp_is_skipped_an_issue'
        )
        self.rp_launch = self.find_option('rp_launch')
        self.rp_launch_id = self.find_option('rp_launch_id')
        self.rp_launch_attributes = self.find_option('rp_launch_attributes')
        self.rp_launch_description = self.find_option('rp_launch_description')
        self.rp_log_batch_size = int(self.find_option('rp_log_batch_size'))
        self.rp_log_level = get_actual_log_level(self.pconfig, 'rp_log_level')
        self.rp_mode = self.find_option('rp_mode')
        self.rp_parent_item_id = self.find_option('rp_parent_item_id')
        self.rp_project = self.find_option('rp_project')
        self.rp_rerun_of = self.find_option('rp_rerun_of')
        self.rp_retries = int(self.find_option('retries'))
        self.rp_uuid = getenv('RP_UUID') or self.find_option('rp_uuid')
        self.rp_verify_ssl = self.find_option('rp_verify_ssl')

    @property
    def rp_rerun(self):
        """Get value of the rp_rerun parameter."""
        if self._rp_rerun is None:
            if self.rp_rerun_of:
                self._rp_rerun = True
            else:
                self._rp_rerun = (self.pconfig.option.rp_rerun or
                                  self.pconfig.getini('rp_rerun'))
        return self._rp_rerun

    def find_option(self, option_name, default=None):
        """
        Find a single configuration setting from multiple places.

        The value is retrieved in the following places in priority order:

        1. From `self.pconfig.option.[option_name]`.
        2. From `self.pconfig.getini(option_name)`.

        :param option_name: name of the option
        :param default:     value to be returned if not found
        :return: option value
        """
        value = (
            getattr(self.pconfig.option, option_name, None) or
            self.pconfig.getini(option_name)
        )
        return value if value else default
