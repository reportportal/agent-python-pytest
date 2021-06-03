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

        self.rp_endpoint = self.pconfig.getini('rp_endpoint')
        self.rp_ignore_errors = self.pconfig.getini('rp_ignore_errors')
        self.rp_ignore_attributes = self.pconfig.getini('rp_ignore_attributes')
        self.rp_is_skipped_an_issue = self.pconfig.getini(
            'rp_is_skipped_an_issue')
        self.rp_launch = self.pconfig.option.rp_launch or self.pconfig.getini(
            'rp_launch')
        self.rp_launch_id = (self.pconfig.option.rp_launch_id or
                             self.pconfig.getini('rp_launch_id'))
        self.rp_launch_attributes = self.pconfig.getini('rp_launch_attributes')
        self.rp_launch_description = (
                self.pconfig.option.rp_launch_description or
                self.pconfig.getini('rp_launch_description')
        )
        self.rp_log_batch_size = int(self.pconfig.getini('rp_log_batch_size'))
        self.rp_log_level = get_actual_log_level(self.pconfig, 'rp_log_level')
        self.rp_parent_item_id = (self.pconfig.option.rp_parent_item_id or
                                  self.pconfig.getini('rp_parent_item_id'))
        self.rp_project = (self.pconfig.option.rp_project or
                           self.pconfig.getini('rp_project'))
        self.rp_rerun_of = (self.pconfig.option.rp_rerun_of or
                            self.pconfig.getini('rp_rerun_of'))
        self.rp_retries = int(self.pconfig.getini('retries'))
        self.rp_uuid = getenv('RP_UUID') or self.pconfig.getini('rp_uuid')
        self.rp_verify_ssl = self.pconfig.getini('rp_verify_ssl')

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
