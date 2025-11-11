#  Copyright (c) 2023 https://reportportal.io .
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

"""This module contains changed pytest for ReportPortal."""

import logging
import os.path
import time
from logging import Logger
from typing import Any, Callable, Dict, Generator

import _pytest.logging
import dill as pickle
import pytest

# noinspection PyPackageRequirements
from pytest import Item, Session
from reportportal_client import RP, RPLogHandler
from reportportal_client.errors import ResponseError

from pytest_reportportal import LAUNCH_WAIT_TIMEOUT
from pytest_reportportal.config import AgentConfig
from pytest_reportportal.rp_logging import patching_logger_class, patching_thread_class
from pytest_reportportal.service import PyTestService

try:
    # noinspection PyPackageRequirements
    from pytest_bdd.parser import Feature, Scenario, Step

    PYTEST_BDD = True
except ImportError:
    Feature = type("dummy", (), {})
    Scenario = type("dummy", (), {})
    Step = type("dummy", (), {})
    PYTEST_BDD = False

LOGGER: Logger = logging.getLogger(__name__)

MANDATORY_PARAMETER_MISSED_PATTERN: str = (
    "One of the following mandatory parameters is unset: " + "rp_project: {}, rp_endpoint: {}"
)

FAILED_LAUNCH_WAIT: str = (
    "Failed to initialize reportportal-client service. "
    + "Waiting for Launch start timed out. "
    + "Reporting is disabled."
)


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: Any) -> None:
    """Configure xdist node controller.

    :param node: Object of the xdist WorkerController class
    """
    # noinspection PyProtectedMember
    if not node.config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return
    node.workerinput["py_test_service"] = pickle.dumps(node.config.py_test_service)


# no 'config' type for backward compatibility for older pytest versions
def is_control(config) -> bool:
    """Validate workerinput attribute of the Config object.

    True if the code, running the given pytest.config object,
    is running as the xdist control node or not running xdist at all.
    """
    return not hasattr(config, "workerinput")


def wait_launch(rp_client: RP) -> bool:
    """Wait for the launch startup.

    :param rp_client: Instance of the ReportPortalService class
    """
    timeout = time.time() + LAUNCH_WAIT_TIMEOUT
    while not rp_client.launch_id:
        if time.time() > timeout:
            return False
        time.sleep(1)
    return True


# noinspection PyProtectedMember
def pytest_sessionstart(session: Session) -> None:
    """Start Report Portal launch.

    This method is called every time on control or worker process start, it
    analyses from which process it is called and starts a Report Portal launch
    if it's a control process.
    :param session: Object of the pytest Session class
    """
    config = session.config
    if not config._rp_enabled:
        return

    try:
        config.py_test_service.start()
    except ResponseError as response_error:
        LOGGER.warning("Failed to initialize reportportal-client service. " "Reporting is disabled.")
        LOGGER.debug(str(response_error))
        config.py_test_service.rp = None
        config._rp_enabled = False
        return

    if is_control(config):
        config.py_test_service.start_launch()
        if config.pluginmanager.hasplugin("xdist") or config.pluginmanager.hasplugin("pytest-parallel"):
            if not wait_launch(session.config.py_test_service.rp):
                LOGGER.error(FAILED_LAUNCH_WAIT)
                config.py_test_service.rp = None
                config._rp_enabled = False


def pytest_collection_finish(session: Session) -> None:
    """Collect tests if session is configured.

    :param session: Object of the pytest Session class
    """
    # noinspection PyProtectedMember
    if not session.config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return

    session.config.py_test_service.collect_tests(session)


# noinspection PyProtectedMember
def pytest_sessionfinish(session: Session) -> None:
    """Finish current test session.

    :param session: Object of the pytest Session class
    """
    config = session.config
    if not config._rp_enabled:
        # Stop now if the plugin is not properly configured
        return

    config.py_test_service.finish_suites()
    if is_control(config):
        config.py_test_service.finish_launch()

    config.py_test_service.stop()


# no 'config' type for backward compatibility for older pytest versions
def register_markers(config) -> None:
    """Register plugin's markers, to avoid declaring them in `pytest.ini`.

    :param config: Object of the pytest Config class
    """
    config.addinivalue_line(
        "markers",
        "issue(issue_id, reason, issue_type, url): mark test with " "information about skipped or failed result",
    )
    config.addinivalue_line(
        "markers",
        "tc_id(id, parameterized, params): report the test"
        "case with a custom Test Case ID. Parameters: \n"
        "parameterized [True / False] - use parameter values in "
        "Test Case ID generation \n"
        "params [parameter names as list] - use only specified"
        "parameters",
    )
    config.addinivalue_line("markers", "name(name): report the test case with a custom Name.")


# no 'config' type for backward compatibility for older pytest versions
# noinspection PyProtectedMember
def pytest_configure(config) -> None:
    """Update Config object with attributes required for reporting to RP.

    :param config: Object of the pytest Config class
    """
    register_markers(config)

    config._rp_enabled = not (
        config.getoption("--collect-only", default=False)
        or config.getoption("--setup-plan", default=False)
        or not config.option.rp_enabled
    )
    if not config._rp_enabled:
        LOGGER.debug("Disabling reporting to RP.")
        return

    agent_config = AgentConfig(config)
    cond = (agent_config.rp_project, agent_config.rp_endpoint)
    config._rp_enabled = all(cond)
    if not config._rp_enabled:
        LOGGER.debug(MANDATORY_PARAMETER_MISSED_PATTERN.format(*cond))
        LOGGER.debug("Disabling reporting to RP.")
        return

    config._reporter_config = agent_config

    if is_control(config):
        config.py_test_service = PyTestService(agent_config)
    else:
        # noinspection PyUnresolvedReferences
        config.py_test_service = pickle.loads(config.workerinput["py_test_service"])


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtestloop(session: Session) -> Generator[None, Any, None]:
    """
    Control start and finish of all test items in the session.

    :param session: pytest.Session
    :return:     generator object
    """
    config = session.config
    if not config._rp_enabled:
        yield
        return

    agent_config = config._reporter_config
    with patching_thread_class(agent_config):
        yield


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: Item) -> Generator[None, Any, None]:
    """Control start and finish of pytest items.

    :param item: Pytest.Item
    :return:     generator object
    """
    config = item.config
    if not config._rp_enabled:
        yield
        return

    service = config.py_test_service
    agent_config = config._reporter_config
    service.start_pytest_item(item)

    log_level = agent_config.rp_log_level or logging.NOTSET
    log_handler = RPLogHandler(
        level=log_level,
        filter_client_logs=True,
        endpoint=agent_config.rp_endpoint,
        ignored_record_names=("reportportal_client", "pytest_reportportal"),
    )
    log_format = agent_config.rp_log_format
    if log_format:
        log_handler.setFormatter(logging.Formatter(log_format))
    with patching_logger_class():
        with _pytest.logging.catching_logs(log_handler, level=log_level):
            yield

    service.finish_pytest_item(item)


# noinspection PyProtectedMember
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item) -> Generator[None, Any, None]:
    """Change runtest_makereport function.

    :param item: pytest.Item
    :return: None
    """
    result = yield
    if not item.config._rp_enabled:
        return
    report = result.get_result()
    service = item.config.py_test_service
    service.process_results(item, report)


def report_fixture(request, fixturedef, name: str, error_msg: str) -> Generator[None, Any, None]:
    """Report fixture setup and teardown.

    :param request:    Object of the FixtureRequest class
    :param fixturedef: represents definition of the texture class
    :param name:       Name of the fixture
    :param error_msg:  Error message
    """
    config = request.config
    enabled = getattr(config, "_rp_enabled", False)
    service = getattr(config, "py_test_service", None)
    agent_config = getattr(config, "_reporter_config", object())
    report_fixtures = getattr(agent_config, "rp_report_fixtures", False)
    if not enabled or not service or not report_fixtures:
        yield
        return

    cached_result = getattr(fixturedef, "cached_result", None)
    if cached_result and hasattr(cached_result, "__getitem__"):
        result = fixturedef.cached_result[2]
        if hasattr(result, "__getitem__"):
            result = result[0]
        if result and isinstance(result, BaseException):
            yield
            return

    yield from service.report_fixture(name, error_msg)


# no types for backward compatibility for older pytest versions
@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request) -> Generator[None, Any, None]:
    """Report fixture setup.

    :param fixturedef: represents definition of the texture class
    :param request:    represents fixture execution metadata
    """
    yield from report_fixture(
        request,
        fixturedef,
        f"{fixturedef.scope} fixture setup: {fixturedef.argname}",
        f"{fixturedef.scope} fixture setup failed: {fixturedef.argname}",
    )


# no types for backward compatibility for older pytest versions
@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_post_finalizer(fixturedef, request) -> Generator[None, Any, None]:
    """Report fixture teardown.

    :param fixturedef: represents definition of the texture class
    :param request:    represents fixture execution metadata
    """
    yield from report_fixture(
        request,
        fixturedef,
        f"{fixturedef.scope} fixture teardown: {fixturedef.argname}",
        f"{fixturedef.scope} fixture teardown failed: {fixturedef.argname}",
    )


if PYTEST_BDD:

    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_before_scenario(request, feature: Feature, scenario: Scenario) -> Generator[None, Any, None]:
        """Report BDD scenario start.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return
        service = config.py_test_service
        service.start_bdd_scenario(feature, scenario)
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_after_scenario(request, feature: Feature, scenario: Scenario) -> Generator[None, Any, None]:
        """Report BDD scenario finish.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return

        yield
        service = config.py_test_service
        service.finish_bdd_scenario(feature, scenario)

    # noinspection PyUnusedLocal
    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_before_step(
        request, feature: Feature, scenario: Scenario, step: Step, step_func: Callable[..., Any]
    ) -> Generator[None, Any, None]:
        """Report BDD step start.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        :param step: represents step from scenario
        :param step_func: represents function for step
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return

        service = config.py_test_service
        service.start_bdd_step(feature, scenario, step)
        yield

    # noinspection PyUnusedLocal
    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_after_step(
        request,
        feature: Feature,
        scenario: Scenario,
        step: Step,
        step_func: Callable[..., Any],
        step_func_args: Dict[str, Any],
    ) -> Generator[None, Any, None]:
        """Report BDD step finish.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        :param step: represents step from scenario
        :param step_func: represents function for step
        :param step_func_args: represents arguments for step function
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return

        yield
        service = config.py_test_service
        service.finish_bdd_step(feature, scenario, step)

    # noinspection PyUnusedLocal
    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_step_error(
        request,
        feature: Feature,
        scenario: Scenario,
        step: Step,
        step_func: Callable[..., Any],
        step_func_args: Dict[str, Any],
        exception,
    ) -> Generator[None, Any, None]:
        """Report BDD step error.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        :param step: represents step from scenario
        :param step_func: represents function for step
        :param step_func_args: represents arguments for step function
        :param exception: represents exception
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return

        yield
        service = config.py_test_service
        service.finish_bdd_step_error(feature, scenario, step, exception)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_bdd_step_func_lookup_error(
        request, feature: Feature, scenario: Scenario, step: Step, exception
    ) -> Generator[None, Any, None]:
        """Report BDD step lookup error.

        :param request: represents item execution metadata
        :param feature: represents feature file
        :param scenario: represents scenario from feature file
        :param step: represents step from scenario
        :param exception: represents exception
        """
        config = request.config
        # noinspection PyProtectedMember
        if not config._rp_enabled:
            yield
            return

        service = config.py_test_service
        service.start_bdd_step(feature, scenario, step)
        yield
        service.finish_bdd_step_error(feature, scenario, step, exception)


# no types for backward compatibility for older pytest versions
def pytest_addoption(parser) -> None:
    """Add support for the RP-related options.

    :param parser: Object of the Parser class
    """
    group = parser.getgroup("reporting")

    def add_shared_option(name, help_str, default=None, action="store"):
        """
        Add an option to both the command line and the .ini file.

        This function modifies `parser` and `group` from the outer scope.

        :param name:     name of the option
        :param help_str: help message
        :param default:  default value
        :param action:   `group.addoption` action
        """
        parser.addini(
            name=name,
            default=default,
            help=help_str,
        )
        group.addoption(
            "--{0}".format(name.replace("_", "-")),
            action=action,
            dest=name,
            help="{help} (overrides {name} config option)".format(
                help=help_str,
                name=name,
            ),
        )

    group.addoption(
        "--reportportal", action="store_true", dest="rp_enabled", default=False, help="Enable ReportPortal plugin"
    )
    add_shared_option(
        name="rp_launch",
        help_str="Launch name",
        default="Pytest Launch",
    )
    add_shared_option(
        name="rp_launch_id",
        help_str="Use already existing launch-id. The plugin won't control " "the Launch status",
    )
    add_shared_option(
        name="rp_launch_description",
        help_str="Launch description",
        default="",
    )
    add_shared_option(name="rp_project", help_str="Project name")
    add_shared_option(
        name="rp_log_level",
        help_str="Logging level for automated log records reporting",
    )
    add_shared_option(
        name="rp_log_format",
        help_str="Logging format for automated log records reporting",
    )
    add_shared_option(
        name="rp_rerun",
        help_str="Marks the launch as a rerun",
        default=False,
        action="store_true",
    )
    add_shared_option(
        name="rp_rerun_of",
        help_str="ID of the launch to be marked as a rerun (use only with " "rp_rerun=True)",
        default="",
    )
    add_shared_option(
        name="rp_parent_item_id",
        help_str="Create all test item as child items of the given (already " "existing) item.",
    )
    add_shared_option(name="rp_api_key", help_str="API key of Report Portal. Usually located on UI profile " "page.")
    add_shared_option(name="rp_endpoint", help_str="Server endpoint")
    add_shared_option(name="rp_mode", help_str="Visibility of current launch [DEFAULT, DEBUG]", default="DEFAULT")
    add_shared_option(
        name="rp_thread_logging",
        help_str="EXPERIMENTAL: Report logs from threads. "
        "This option applies a patch to the builtin Thread class, "
        "and so it is turned off by default. Use with caution.",
        default=False,
        action="store_true",
    )
    add_shared_option(
        name="rp_launch_uuid_print",
        help_str="Enables printing Launch UUID on test run start. Possible values: [True, False]",
    )
    add_shared_option(
        name="rp_launch_uuid_print_output",
        help_str="Launch UUID print output. Default `stdout`. Possible values: [stderr, stdout]",
    )

    # OAuth 2.0 parameters
    parser.addini("rp_oauth_uri", type="args", help="OAuth 2.0 token endpoint URL for password grant authentication")
    parser.addini("rp_oauth_username", type="args", help="OAuth 2.0 username for password grant authentication")
    parser.addini("rp_oauth_password", type="args", help="OAuth 2.0 password for password grant authentication")
    parser.addini("rp_oauth_client_id", type="args", help="OAuth 2.0 client identifier")
    parser.addini("rp_oauth_client_secret", type="args", help="OAuth 2.0 client secret")
    parser.addini("rp_oauth_scope", type="args", help="OAuth 2.0 access token scope")

    parser.addini("rp_launch_attributes", type="args", help="Launch attributes, i.e Performance Regression")
    parser.addini("rp_tests_attributes", type="args", help="Attributes for all tests items, e.g. Smoke")
    parser.addini("rp_log_batch_size", default="20", help="Size of batch log requests in async mode")
    parser.addini(
        "rp_log_batch_payload_limit",
        help="Maximum payload size in bytes of async batch log requests",
    )
    parser.addini(
        "rp_log_batch_payload_size",
        help="DEPRECATED: Maximum payload size in bytes of async batch log requests",
    )
    parser.addini("rp_ignore_attributes", type="args", help="Ignore specified pytest markers, i.e parametrize")
    parser.addini(
        "rp_is_skipped_an_issue", default=True, type="bool", help="Treat skipped tests as required investigation"
    )
    parser.addini("rp_hierarchy_code", default=False, type="bool", help="Enables hierarchy for code")
    parser.addini("rp_hierarchy_dirs_level", default="0", help="Directory starting hierarchy level")
    parser.addini("rp_hierarchy_dirs", default=False, type="bool", help="Enables hierarchy for directories")
    parser.addini(
        "rp_hierarchy_dir_path_separator",
        default=os.path.sep,
        help="Path separator to display directories in test hierarchy",
    )
    parser.addini("rp_hierarchy_test_file", default=True, type="bool", help="Show file name in hierarchy")
    parser.addini(
        "rp_issue_system_url",
        default="",
        help="URL to get issue description. Issue id from pytest mark will be added to this URL. "
        'Deprecated: use "rp_bts_issue_url".',
    )
    parser.addini(
        "rp_bts_issue_url",
        default="",
        help="URL to get issue description. Issue ID from pytest mark will be added to this URL by replacing "
        '"{issue_id}" placeholder.',
    )
    parser.addini(
        "rp_bts_project",
        default="",
        help="Bug-tracking system project as it configured on Report Portal "
        "server. To enable runtime external issue reporting you need to "
        'specify this and "rp_bts_url" property.',
    )
    parser.addini(
        "rp_bts_url",
        default="",
        help="URL of bug-tracking system as it configured on Report Portal "
        "server. To enable runtime external issue reporting you need to "
        'specify this and "rp_bts_project" property.',
    )
    parser.addini(
        "rp_verify_ssl",
        default="True",
        help="True/False - verify HTTPS calls, or path to a CA_BUNDLE or "
        "directory with certificates of trusted CAs.",
    )
    parser.addini("rp_issue_id_marks", type="bool", default=True, help="Add tag with issue id to the test")
    parser.addini("retries", default="0", help="Deprecated: use `rp_api_retries` instead")
    parser.addini("rp_api_retries", default="0", help="Amount of retries for performing REST calls to RP server")
    parser.addini(
        "rp_launch_timeout",
        default=86400,
        help="Maximum time to wait for child processes finish, default value: " "86400 seconds (1 day)",
    )
    parser.addini(
        "rp_client_type",
        help="Type of the under-the-hood ReportPortal client implementation. Possible values: [SYNC, ASYNC_THREAD, "
        "ASYNC_BATCHED]",
    )
    parser.addini("rp_connect_timeout", help="Connection timeout to ReportPortal server")
    parser.addini("rp_read_timeout", help="Response read timeout for ReportPortal connection")
    parser.addini(
        "rp_report_fixtures",
        default=False,
        type="bool",
        help="Enable reporting fixtures as test items. Possible values: [True, False]",
    )
