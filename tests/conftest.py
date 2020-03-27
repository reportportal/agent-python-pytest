"""This module contains common Pytest fixtures and hooks for unit tests."""

from six.moves import mock

from _pytest.config import Config
from pytest import fixture

from pytest_reportportal import RPLogger
from pytest_reportportal.listener import RPReportListener
from pytest_reportportal.service import PyTestServiceClass


@fixture
def logger():
    """Prepare instance of the RPLogger for testing."""
    return RPLogger('pytest_reportportal.test')


@fixture()
def mocked_item(mocked_session):
    """Mock Pytest item for testing."""
    test_item = mock.Mock()
    test_item.session = mocked_session
    return test_item


@fixture()
def mocked_config():
    """Mock Pytest config for testing."""
    mocked_config = mock.create_autospec(Config)
    mocked_config._reportportal_configured = True
    return mocked_config


@fixture()
def mocked_session(mocked_config):
    """Mock Pytest session for testing."""
    mocked_session = mock.Mock()
    mocked_session.config = mocked_config
    return mocked_session


@fixture(scope='session')
def rp_listener(rp_service):
    """Prepare instance of the RPReportListener for testing."""
    return RPReportListener(rp_service)


@fixture(scope='session')
def rp_service():
    """Prepare instance of the PyTestServiceClass for testing."""
    service = PyTestServiceClass()
    with mock.patch('reportportal_client.service.'
                    'ReportPortalService.get_project_settings'):
        service.init_service("endpoint", "project", "uuid", 20, False, [])
        return service


@fixture(scope="session")
def code_ref(request):
    """Return the directory of the currently running test script."""

    return request.fspath
