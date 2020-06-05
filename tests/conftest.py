"""This module contains common Pytest fixtures and hooks for unit tests."""

from six.moves import mock

import py
from _pytest.config import Config
from _pytest.main import Session
from pytest import fixture
from pluggy._tracing import TagTracer

from pytest_reportportal import RPLogger
from pytest_reportportal.listener import RPReportListener
from pytest_reportportal.service import PyTestServiceClass


@fixture
def logger():
    """Prepare instance of the RPLogger for testing."""
    return RPLogger('pytest_reportportal.test')


@fixture()
def mocked_item(mocked_session, mocked_module):
    """Mock Pytest item for testing."""
    test_item = mock.Mock()
    test_item.session = mocked_session
    test_item.fspath = py.path.local('/path/to/test')
    test_item.name = 'test_item'
    test_item.parent = mocked_module
    return test_item


@fixture()
def mocked_module(mocked_session):
    """Mock Pytest Module for testing."""
    mocked_module = mock.Mock()
    mocked_module.parent = mocked_session
    return mocked_module


@fixture()
def mocked_config():
    """Mock Pytest config for testing."""
    mocked_config = mock.create_autospec(Config)
    mocked_config._reportportal_configured = True
    mocked_config.rootdir = py.path.local('/path/to')
    mocked_config.trace = TagTracer().get('root')
    mocked_config.pluginmanager = mock.Mock()
    return mocked_config


@fixture()
def mocked_session(mocked_config):
    """Mock Pytest session for testing."""
    mocked_session = mock.create_autospec(Session)
    mocked_session.config = mocked_config
    return mocked_session


@fixture()
def rp_listener(rp_service):
    """Prepare instance of the RPReportListener for testing."""
    return RPReportListener(rp_service)


@fixture()
def rp_service():
    """Prepare instance of the PyTestServiceClass for testing."""
    service = PyTestServiceClass()
    with mock.patch('reportportal_client.service.'
                    'ReportPortalService.get_project_settings'):
        service.init_service("endpoint", "project", "uuid", 20, False, [])
        return service
