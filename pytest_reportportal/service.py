"""This module includes Service functions for work with pytest agent."""

import logging
import os.path
import sys
import threading
from os import getenv
from time import time

from _pytest.doctest import DoctestItem
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.python import Class, Function, Instance, Module, Package
from _pytest.warning_types import PytestWarning
from aenum import auto, Enum, unique
from reportportal_client.client import RPClient
from reportportal_client.external.google_analytics import send_event
from reportportal_client.helpers import (
    gen_attributes,
    get_launch_sys_attrs,
    get_package_version
)
from reportportal_client.service import _dict_to_payload

log = logging.getLogger(__name__)

MAX_ITEM_NAME_LENGTH = 256
TRUNCATION_STR = '...'


def timestamp():
    """Time for difference between start and finish tests."""
    return str(int(time() * 1000))


def trim_docstring(docstring):
    """
    Convert docstring.

    :param docstring: input docstring
    :return: docstring
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


@unique
class LeafType(Enum):
    """This class stores test item path types."""

    DIR = auto()
    CODE = auto()
    ROOT = auto()


@unique
class ExecStatus(Enum):
    """This class stores test item path types."""

    CREATED = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()


class PyTestServiceClass(object):
    """Pytest service class for reporting test results to the Report Portal."""

    def __init__(self, agent_config):
        """Initialize instance attributes."""
        self._config = agent_config
        self._issue_types = {}
        self._item_parts = {}
        self._loglevels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')
        self._skip_analytics = getenv('AGENT_NO_ANALYTICS')
        self.agent_name = 'pytest-reportportal'
        self.agent_version = get_package_version(self.agent_name)
        self.ignored_attributes = []
        self.log_batch_size = 20
        self.log_item_id = None
        self.parent_item_id = None
        self.rp = None
        self.project_settings = {}

    @property
    def issue_types(self):
        """Issue types for the Report Portal project."""
        if not self._issue_types:
            if not self.project_settings:
                return self._issue_types
            for item_type in ("AUTOMATION_BUG", "PRODUCT_BUG", "SYSTEM_ISSUE",
                              "NO_DEFECT", "TO_INVESTIGATE"):
                for item in self.project_settings["subTypes"][item_type]:
                    self._issue_types[item["shortName"]] = item["locator"]
        return self._issue_types

    def init_service(self):
        """Update self.rp with the instance of the ReportPortalService."""
        if self.rp is None:
            self.parent_item_id = self._config.rp_parent_item_id
            self.ignored_attributes = list(
                set(self._config.rp_ignore_attributes or [])
                    .union({'parametrize'})
            )
            log.debug('ReportPortal - Init service: endpoint=%s, '
                      'project=%s, uuid=%s', self._config.rp_endpoint,
                      self._config.rp_project, self._config.rp_uuid)
            self.rp = RPClient(
                endpoint=self._config.rp_endpoint,
                project=self._config.rp_project,
                token=self._config.rp_uuid,
                is_skipped_an_issue=self._config.rp_is_skipped_an_issue,
                log_batch_size=self._config.rp_log_batch_size,
                retries=self._config.rp_retries,
                verify_ssl=self._config.rp_verify_ssl,
                launch_id=self._config.rp_launch_id,
            )
            self.project_settings = None
            if self.rp and hasattr(self.rp, "get_project_settings"):
                self.project_settings = self.rp.get_project_settings()
            self.rp.start()
        else:
            log.debug('The pytest is already initialized')
        return self.rp

    def _build_start_launch_rq(self):
        rp_launch_attributes = self._config.rp_launch_attributes
        attributes = gen_attributes(rp_launch_attributes) \
            if rp_launch_attributes else None

        start_rq = {
            'attributes': self._get_launch_attributes(attributes),
            'name': self._config.rp_launch,
            'start_time': timestamp(),
            'description': self._config.rp_launch_description,
            'mode': self._config.rp_mode,
            'rerun': self._config.rp_rerun,
            'rerun_of': self._config.rp_rerun_of
        }
        return start_rq

    def start_launch(self):
        """
        Launch test items.

        :return: item ID
        """
        if self.rp is None:
            return
        sl_pt = self._build_start_launch_rq()
        log.debug('ReportPortal - Start launch: request_body=%s', sl_pt)
        item_id = self.rp.start_launch(**sl_pt)
        log.debug('ReportPortal - Launch started: id=%s', item_id)
        if not self._skip_analytics:
            send_event(self.agent_name, self.agent_version)
        return item_id

    @staticmethod
    def _get_item_dirs(item):
        """
        Get directory of item.

        :param item: pytest.Item
        :return: list of dirs
        """
        root_path = item.session.config.rootdir.strpath
        dir_path = item.fspath.new(basename="")
        rel_dir = dir_path.new(dirname=dir_path.relto(root_path), basename="",
                               drive="")
        return [d for d in rel_dir.parts(reverse=False) if d.basename]

    @staticmethod
    def _get_item_parts(item):
        """
        Get item of parents.

        :param item: pytest.Item
        :return list of parents
        """
        parts = [item]
        parent = item.parent
        while parent is not None and not isinstance(parent, Session):
            if not isinstance(parent, Instance):
                parts.append(parent)
            parent = parent.parent

        parts.reverse()
        return parts

    def _build_test_tree(self, session):
        test_tree = {'children': {}, 'status': 'PASSED', 'type': LeafType.ROOT,
                     'item_id': self.parent_item_id}

        for item in session.items:
            dir_path = PyTestServiceClass._get_item_dirs(item)
            class_path = PyTestServiceClass._get_item_parts(item)

            current_node = test_tree
            for i, path_part in enumerate(dir_path + class_path):
                children = current_node['children']

                node_type = LeafType.DIR
                if i >= len(dir_path):
                    node_type = LeafType.CODE

                if path_part not in children:
                    children[path_part] = {
                        'children': {}, 'status': 'PASSED', 'type': node_type,
                        'parent': current_node, 'start_flag': False,
                        'item': path_part, 'lock': threading.Lock(),
                        'exec': ExecStatus.CREATED, 'finish_flag': False
                    }
                current_node = children[path_part]
        return test_tree

    @staticmethod
    def _remove_root_package(test_tree):
        if test_tree['type'] == LeafType.ROOT or \
                test_tree['type'] == LeafType.DIR:
            for item, child_node in test_tree['children'].items():
                PyTestServiceClass._remove_root_package(child_node)
                return
        if test_tree['type'] == LeafType.CODE and \
                isinstance(test_tree['item'], Package) and \
                test_tree['parent']['type'] == LeafType.DIR:
            parent_node = test_tree['parent']
            current_item = test_tree['item']
            del parent_node['children'][current_item]
            for item, child_node in test_tree['children'].items():
                parent_node['children'][item] = child_node
                child_node['parent'] = parent_node

    @staticmethod
    def _remove_root_dirs(test_tree, max_dir_level, dir_level=0):
        if test_tree['type'] == LeafType.ROOT:
            for item, child_node in test_tree['children'].items():
                PyTestServiceClass._remove_root_dirs(child_node, max_dir_level,
                                                     1)
                return
        if test_tree['type'] == LeafType.DIR and dir_level <= max_dir_level:
            new_level = dir_level + 1
            parent_node = test_tree['parent']
            current_item = test_tree['item']
            del parent_node['children'][current_item]
            for item, child_node in test_tree['children'].items():
                parent_node['children'][item] = child_node
                child_node['parent'] = parent_node
                PyTestServiceClass._remove_root_dirs(test_tree, max_dir_level,
                                                     new_level)

    @staticmethod
    def _generate_names(test_tree):
        if test_tree['type'] == LeafType.ROOT:
            test_tree['name'] = 'root'

        if test_tree['type'] == LeafType.DIR:
            test_tree['name'] = test_tree['item'].basename

        if test_tree['type'] == LeafType.CODE:
            item = test_tree['item']
            if isinstance(item, Package):
                test_tree['name'] = \
                    os.path.split(os.path.split(item.fspath)[0])[1]
            elif isinstance(item, Module):
                test_tree['name'] = os.path.split(item.fspath)[1]
            else:
                test_tree['name'] = item.name

        for item, child_node in test_tree['children'].items():
            PyTestServiceClass._generate_names(child_node)

    def _build_item_paths(self, node, path):
        if 'children' in node and len(node['children']) > 0:
            path.append(node)
            for name, child_node in node['children'].items():
                self._build_item_paths(child_node, path)
            path.pop()
        else:
            self._item_parts[node['item']] = path + [node]

    def collect_tests(self, session):
        """
        Collect all tests.

        :param session: pytest.Session
        """
        if self.rp is None:
            return

        # Create a test tree to be able to apply mutations
        test_tree = self._build_test_tree(session)
        self._remove_root_package(test_tree)
        self._remove_root_dirs(test_tree, self._config.rp_dir_level)
        self._generate_names(test_tree)

        self._build_item_paths(test_tree, [])

    # noinspection PyMethodMayBeStatic
    def _lock(self, part, func):
        if 'lock' in part:
            with part['lock']:
                result = func(part)
        else:
            result = func(part)
        return result

    def _build_start_suite_rq(self, part):
        code_ref = str(part['item']) if part['type'] == LeafType.DIR \
            else str(part['item'].fspath)
        payload = {
            'name': self._get_item_name(part['name']),
            'description': self._get_item_description(part['item']),
            'start_time': timestamp(),
            'item_type': 'SUITE',
            'code_ref': code_ref,
            'parent_item_id': self._lock(part['parent'],
                                         lambda p: p['item_id'])
        }
        return payload

    def _start_suite(self, suite_rq):
        log.debug('ReportPortal - Start Suite: request_body=%s',
                  suite_rq)
        return self.rp.start_test_item(**suite_rq)

    def _open_suite(self, part):
        if part['start_flag']:
            return
        item_id = self._start_suite(self._build_start_suite_rq(part))
        part['item_id'] = item_id
        self.log_item_id = item_id
        part['start_flag'] = True

    def _create_suite_path(self, item):
        if self.rp is None:
            return

        path = self._item_parts[item]
        for part in path[1:-1]:
            if part['start_flag']:
                continue
            self._lock(part, lambda p: self._open_suite(p))

    def _build_start_step_rq(self, part):
        code_ref = '{0}:{1}'.format(part['item'].fspath, part['name'])
        payload = {
            'attributes': self._get_item_markers(part['item']),
            'name': self._get_item_name(part['name']),
            'description': self._get_item_description(part['item']),
            'start_time': timestamp(),
            'item_type': 'STEP',
            'code_ref': code_ref,
            'parameters': self._get_parameters(part['item']),
            'parent_item_id': self._lock(part['parent'],
                                         lambda p: p['item_id'])
        }
        return payload

    def _start_step(self, step_rq):
        log.debug('ReportPortal - Start TestItem: request_body=%s', step_rq)
        return self.rp.start_test_item(**step_rq)

    def start_pytest_item(self, test_item=None):
        """
        Start pytest_item.

        :param test_item: pytest.Item
        :return: item ID
        """
        if self.rp is None or test_item is None:
            return

        self._create_suite_path(test_item)

        # Item type should be sent as "STEP" until we upgrade to RPv6.
        # Details at:
        # https://github.com/reportportal/agent-Python-RobotFramework/issues/56
        current_part = self._item_parts[test_item][-1]
        item_id = self._start_step(self._build_start_step_rq(current_part))
        current_part['item_id'] = item_id
        current_part['exec'] = ExecStatus.IN_PROGRESS
        self.log_item_id = item_id

    # noinspection PyMethodMayBeStatic
    def _build_finish_step_rq(self, part, issue):
        payload = {
            'end_time': timestamp(),
            'status': part['status'],
            'issue': issue,
            'item_id': part['item_id']
        }
        return payload

    def _finish_step(self, finish_rq):
        log.debug('ReportPortal - Finish TestItem: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def finish_pytest_item(self, test_item, status, issue=None):
        """
        Finish pytest_item.

        :param test_item: test_item
        :param status:    an item finish status (PASSED, FAILED, STOPPED,
        SKIPPED, RESETED, CANCELLED, INFO, WARN)
        :param issue:     an external system issue reference
        :return: None
        """
        if self.rp is None:
            return

        parts = self._item_parts[test_item]
        item_part = parts[-1]
        item_part['status'] = status
        self._finish_step(self._build_finish_step_rq(item_part, issue))
        item_part['exec'] = ExecStatus.FINISHED

    def _finish_suite(self, finish_rq):
        log.debug('ReportPortal - End TestSuite: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    # noinspection PyMethodMayBeStatic
    def _build_finish_suite_rq(self, part):
        payload = {
            'end_time': timestamp(),
            'status': part['status'],
            'item_id': part['item_id']
        }
        return payload

    def _close_suite(self, part):
        if part['finish_flag']:
            return
        self._finish_suite(self._build_finish_suite_rq(part))
        part['finish_flag'] = True

    def finish_suites(self):
        if self.rp is None:
            return

        for item, path in self._item_parts.items():
            my_path = list(path)
            my_path.reverse()
            for part in my_path[1:-1]:
                if 'item_id' in part:
                    if part['finish_flag']:
                        continue
                    self._lock(part, lambda p: self._close_suite(p))

    # noinspection PyMethodMayBeStatic
    def _build_finish_launch_rq(self, status):
        finish_rq = {
            'end_time': timestamp(),
            'status': status
        }
        return finish_rq

    def _finish_launch(self, finish_rq):
        log.debug('ReportPortal - Finish launch: request_body=%s', finish_rq)
        self.rp.finish_launch(**finish_rq)

    def finish_launch(self, status=None):
        """
        Finish tests launch.

        :param status: an launch status (PASSED, FAILED, STOPPED, SKIPPED,
        INTERRUPTED, CANCELLED, INFO, WARN)
        :return: None
        """
        if self.rp is None:
            return

        # To finish launch session str parameter is needed
        self._finish_launch(self._build_finish_launch_rq(status))
        # self.rp.terminate()
        self.rp = None

    def post_log(self, message, loglevel='INFO', attachment=None):
        """
        Send a log message to the Report Portal.

        :param message:    message in log body
        :param loglevel:   a level of a log entry (ERROR, WARN, INFO, DEBUG,
        TRACE, FATAL, UNKNOWN)
        :param attachment: attachment file
        :return: None
        """
        if self.rp is None:
            return

        if loglevel not in self._loglevels:
            log.warning('Incorrect loglevel = %s. Force set to INFO. '
                        'Available levels: %s.', loglevel, self._loglevels)
            loglevel = 'INFO'

        sl_rq = {
            'item_id': self.log_item_id,
            'time': timestamp(),
            'message': message,
            'level': loglevel,
            'attachment': attachment
        }
        self.rp.log(**sl_rq)

    def _get_launch_attributes(self, ini_attrs):
        """Generate launch attributes in the format supported by the client.

        :param list ini_attrs: List for attributes from the pytest.ini file
        """
        attributes = ini_attrs or []
        system_attributes = get_launch_sys_attrs()
        system_attributes['agent'] = (
            '{}-{}'.format(self.agent_name, self.agent_version))
        return attributes + _dict_to_payload(system_attributes)

    def _get_item_markers(self, item):
        """
        Get attributes of item.

        :param item: pytest.Item
        :return: list of tags
        """
        # Try to extract names of @pytest.mark.* decorators used for test item
        # and exclude those which present in rp_ignore_attributes parameter
        def get_marker_value(my_item, keyword):
            try:
                marker = my_item.get_closest_marker(keyword)
            except AttributeError:
                # pytest < 3.6
                marker = my_item.keywords.get(keyword)

            marker_values = []
            if marker and marker.args:
                for my_arg in marker.args:
                    marker_values.append("{}:{}".format(keyword, my_arg))
            else:
                marker_values.append(keyword)
            # returns a list of strings to accommodate multiple values
            return marker_values

        try:
            get_marker = getattr(item, "get_closest_marker")
        except AttributeError:
            get_marker = getattr(item, "get_marker")

        raw_attrs = []
        for k in item.keywords:
            if get_marker(k) is not None and k not in self.ignored_attributes:
                raw_attrs.extend(get_marker_value(item, k))
        # When we have custom markers with different values, append the
        # raw_attrs with the markers which were missed initially.
        # Adds supports to have two attributes with same keys.
        for cust_marker in item.own_markers:
            for arg in cust_marker.args:
                custom_arg = "{0}:{1}".format(cust_marker.name, arg)
                if not (custom_arg in raw_attrs) and \
                        cust_marker.name not in self.ignored_attributes:
                    raw_attrs.append(custom_arg)
        raw_attrs.extend(item.session.config.getini('rp_tests_attributes'))
        return gen_attributes(raw_attrs)

    # noinspection PyMethodMayBeStatic
    def _get_parameters(self, item):
        """
        Get params of item.

        :param item: Pytest.Item
        :return: dict of params
        """
        return item.callspec.params if hasattr(item, 'callspec') else None

    @staticmethod
    def _get_item_name(name):
        """
        Get name of item.

        :param name: Item name
        :return: name
        """
        if len(name) > MAX_ITEM_NAME_LENGTH:
            name = name[:MAX_ITEM_NAME_LENGTH - len(TRUNCATION_STR)] + \
                   TRUNCATION_STR
            log.warning(
                PytestWarning(
                    'Test node ID was truncated to "{}" because of name size '
                    'constrains on reportportal'.format(name)
                )
            )
        return name

    @staticmethod
    def _get_item_description(test_item):
        """
        Get description of item.

        :param test_item: pytest.Item
        :return string description
        """
        if isinstance(test_item, (Class, Function, Module, Item)):
            if hasattr(test_item, "obj"):
                doc = test_item.obj.__doc__
                if doc is not None:
                    return trim_docstring(doc)
        if isinstance(test_item, DoctestItem):
            return test_item.reportinfo()[2]
