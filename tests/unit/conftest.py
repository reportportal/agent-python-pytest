"""This module contains common Pytest fixtures and hooks for unit tests."""

#  Copyright (c) 2021 https://reportportal.io .
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

import py
from _pytest.config import Config
from _pytest.main import Session
from pluggy._tracing import TagTracer
from pytest import fixture, Module
# noinspection PyUnresolvedReferences
from unittest import mock

from reportportal_client import RPLogger
from pytest_reportportal.config import AgentConfig
from pytest_reportportal.service import PyTestServiceClass
from tests import REPORT_PORTAL_SERVICE

ITEM_PATH = py.path.local('examples/test_simple.py')


@fixture
def logger():
    """Prepare instance of the RPLogger for testing."""
    return RPLogger('pytest_reportportal.test')


@fixture()
def mocked_config():
    """Mock Pytest config for testing."""
    mocked_config = mock.create_autospec(Config)

    mocked_config.getoption_side_effects = {
        '--collect-only': False,
        '--setup-plan': False,
        'rp_log_level': 'debug'
    }

    def getoption_side_effect(name, default=None):
        return mocked_config.getoption_side_effects.get(
            name, default if default else mock.Mock()
        )

    mocked_config._reporter_config = mock.Mock()
    mocked_config.getoption.side_effect = getoption_side_effect
    mocked_config._rp_enabled = True
    mocked_config.rootdir = py.path.local('/path/to')
    mocked_config.trace = TagTracer().get('root')
    mocked_config.pluginmanager = mock.Mock()
    mocked_config.option = mock.create_autospec(Config)
    mocked_config.option.rp_project = 'default_personal'
    mocked_config.option.rp_endpoint = 'http://docker.local:8080/'
    mocked_config.option.rp_api_key = mock.sentinel.rp_api_key
    mocked_config.option.rp_log_batch_size = -1
    mocked_config.option.retries = -1
    mocked_config.option.rp_hierarchy_dirs_level = '0'
    mocked_config.option.rp_rerun = False
    mocked_config.option.rp_launch_timeout = -1
    mocked_config.option.rp_thread_logging = True
    mocked_config.option.rp_launch_uuid_print = 'False'
    return mocked_config


@fixture()
def mocked_session(mocked_config):
    """Mock Pytest session for testing."""
    mocked_session = mock.create_autospec(Session)
    mocked_session.config = mocked_config
    return mocked_session


@fixture()
def mocked_module(mocked_session):
    """Mock Pytest Module for testing."""
    mocked_module = mock.create_autospec(Module)
    mocked_module.parent = mocked_session
    mocked_module.name = 'module'
    mocked_module.fspath = ITEM_PATH
    return mocked_module


@fixture()
def mocked_item(mocked_session, mocked_module):
    """Mock Pytest item for testing."""
    test_item = mock.Mock()
    test_item.session = mocked_session
    test_item.fspath = ITEM_PATH
    name = 'test_item'
    test_item.name = name
    test_item.originalname = name
    test_item.parent = mocked_module
    return test_item


@fixture()
def rp_service(mocked_config):
    """Prepare instance of the PyTestServiceClass for testing."""
    service = PyTestServiceClass(AgentConfig(mocked_config))
    with mock.patch(REPORT_PORTAL_SERVICE + '.get_project_settings'):
        service.start()
        return service
