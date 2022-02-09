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
from _pytest.main import Session, Config
from pluggy._tracing import TagTracer
from pytest import fixture, Module
from six.moves import mock

from pytest_reportportal import RPLogger
from pytest_reportportal.config import AgentConfig
from pytest_reportportal.listener import RPReportListener
from pytest_reportportal.service import PyTestServiceClass
from tests import REPORT_PORTAL_SERVICE


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
    mocked_config._reportportal_configured = True
    mocked_config.rootdir = py.path.local('/path/to')
    mocked_config.trace = TagTracer().get('root')
    mocked_config.pluginmanager = mock.Mock()
    mocked_config.option = mock.create_autospec(Config)
    mocked_config.option.rp_project = mock.sentinel.rp_project
    mocked_config.option.rp_endpoint = mock.sentinel.rp_endpoint
    mocked_config.option.rp_uuid = mock.sentinel.rp_uuid
    mocked_config.option.rp_log_batch_size = -1
    mocked_config.option.retries = -1
    mocked_config.option.rp_hierarchy_dirs_level = '0'
    mocked_config.option.rp_rerun = False
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
    return mocked_module


@fixture()
def mocked_item(mocked_session, mocked_module):
    """Mock Pytest item for testing."""
    test_item = mock.Mock()
    test_item.session = mocked_session
    test_item.fspath = py.path.local('examples/test_simple.py')
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
        service.init_service()
        return service


@fixture()
def rp_listener(rp_service):
    """Prepare instance of the RPReportListener for testing."""
    return RPReportListener(rp_service)
