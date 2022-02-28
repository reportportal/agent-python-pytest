"""This module includes Service functions for work with pytest agent."""

import logging
import os.path
import sys
import threading
from os import getenv, curdir
from time import time, sleep

from _pytest.doctest import DoctestItem
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.warning_types import PytestWarning
from aenum import auto, Enum, unique
from pytest import Class, Function, Module, Package
from reportportal_client.core.rp_issues import Issue

try:
    from pytest import Instance
except ImportError:
    # in pytest >= 7.0 this type was removed
    Instance = type('dummy', (), {})
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
ROOT_DIR = str(os.path.abspath(curdir))
PYTEST_MARKS_IGNORE = {'parametrize', 'usefixtures', 'filterwarnings'}
NOT_ISSUE = Issue('NOT_ISSUE')


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
        self.parent_item_id = None
        self.rp = None
        self.project_settings = {}

    @property
    def issue_types(self):
        """Issue types for the Report Portal project."""
        if not self._issue_types:
            if not self.project_settings:
                return self._issue_types
            for values in self.project_settings["subTypes"].values():
                for item in values:
                    self._issue_types[item["shortName"]] = item["locator"]
        return self._issue_types

    def _get_launch_attributes(self, ini_attrs):
        """Generate launch attributes in the format supported by the client.

        :param list ini_attrs: List for attributes from the pytest.ini file
        """
        attributes = ini_attrs or []
        system_attributes = get_launch_sys_attrs()
        system_attributes['agent'] = (
            '{}-{}'.format(self.agent_name, self.agent_version))
        return attributes + _dict_to_payload(system_attributes)

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

    def _get_item_dirs(self, item):
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

    def _get_item_parts(self, item):
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
            dir_path = self._get_item_dirs(item)
            class_path = self._get_item_parts(item)

            current_node = test_tree
            for i, path_part in enumerate(dir_path + class_path):
                children = current_node['children']

                node_type = LeafType.DIR
                if i >= len(dir_path):
                    node_type = LeafType.CODE

                if path_part not in children:
                    children[path_part] = {
                        'children': {}, 'type': node_type, 'item': path_part,
                        'parent': current_node, 'lock': threading.Lock(),
                        'exec': ExecStatus.CREATED
                    }
                current_node = children[path_part]
        return test_tree

    def _remove_root_package(self, test_tree):
        if test_tree['type'] == LeafType.ROOT or \
                test_tree['type'] == LeafType.DIR:
            for item, child_node in test_tree['children'].items():
                self._remove_root_package(child_node)
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

    def _remove_root_dirs(self, test_tree, max_dir_level, dir_level=0):
        if test_tree['type'] == LeafType.ROOT:
            for item, child_node in test_tree['children'].items():
                self._remove_root_dirs(child_node, max_dir_level, 1)
                return
        if test_tree['type'] == LeafType.DIR and dir_level <= max_dir_level:
            new_level = dir_level + 1
            parent_node = test_tree['parent']
            current_item = test_tree['item']
            del parent_node['children'][current_item]
            for item, child_node in test_tree['children'].items():
                parent_node['children'][item] = child_node
                child_node['parent'] = parent_node
                self._remove_root_dirs(child_node, max_dir_level,
                                       new_level)

    def _generate_names(self, test_tree):
        if test_tree['type'] == LeafType.ROOT:
            test_tree['name'] = 'root'

        if test_tree['type'] == LeafType.DIR:
            test_tree['name'] = test_tree['item'].basename

        if test_tree['type'] == LeafType.CODE:
            item = test_tree['item']
            if isinstance(item, Package):
                test_tree['name'] = \
                    os.path.split(os.path.split(str(item.fspath))[0])[1]
            elif isinstance(item, Module):
                test_tree['name'] = os.path.split(str(item.fspath))[1]
            else:
                test_tree['name'] = item.name

        for item, child_node in test_tree['children'].items():
            self._generate_names(child_node)

    def _merge_node_type(self, test_tree, node_type, separator):
        child_items = list(test_tree['children'].items())
        if test_tree['type'] != node_type:
            for item, child_node in child_items:
                self._merge_node_type(child_node, node_type, separator)
        elif len(test_tree['children'].items()) > 0:
            parent_node = test_tree['parent']
            current_item = test_tree['item']
            current_name = test_tree['name']
            del parent_node['children'][current_item]
            for item, child_node in child_items:
                parent_node['children'][item] = child_node
                child_node['parent'] = parent_node
                child_node['name'] = \
                    current_name + separator + child_node['name']
                self._merge_node_type(child_node, node_type, separator)

    def _merge_dirs(self, test_tree):
        self._merge_node_type(test_tree, LeafType.DIR,
                              self._config.rp_dir_path_separator)

    def _merge_code(self, test_tree):
        self._merge_node_type(test_tree, LeafType.CODE, '::')

    def _build_item_paths(self, node, path):
        if 'children' in node and len(node['children']) > 0:
            path.append(node)
            for name, child_node in node['children'].items():
                self._build_item_paths(child_node, path)
            path.pop()
        elif node['type'] != LeafType.ROOT:
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
        if not self._config.rp_hierarchy_dirs:
            self._merge_dirs(test_tree)
        if not self._config.rp_hierarchy_code:
            self._merge_code(test_tree)
        self._build_item_paths(test_tree, [])

    def _get_item_name(self, name):
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

    def _get_item_description(self, test_item):
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

    def _lock(self, node, func):
        """
        Lock test tree node and execute a function, bypass the node to it.

        :param node: a node to lock
        :param func: a function to execute
        :return: the result of the function bypassed
        """
        if 'lock' in node:
            with node['lock']:
                return func(node)
        return func(node)

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

    def _create_suite(self, part):
        if part['exec'] != ExecStatus.CREATED:
            return
        item_id = self._start_suite(self._build_start_suite_rq(part))
        part['item_id'] = item_id
        part['exec'] = ExecStatus.IN_PROGRESS

    def _create_suite_path(self, item):
        if self.rp is None:
            return

        path = self._item_parts[item]
        for part in path[1:-1]:
            if part['exec'] != ExecStatus.CREATED:
                continue
            self._lock(part, lambda p: self._create_suite(p))

    def _get_code_ref(self, item):
        # Generate script path from work dir, use only backslashes to have the
        # same path on different systems and do not affect Test Case ID on
        # different systems
        path = os.path.relpath(str(item.fspath), ROOT_DIR).replace('\\', '/')
        method_name = item.originalname if item.originalname is not None \
            else item.name
        parent = item.parent
        classes = [method_name]
        while not isinstance(parent, Module):
            if not isinstance(parent, Instance):
                classes.append(parent.name)
            parent = parent.parent
        classes.reverse()
        class_path = '.'.join(classes)
        return '{0}:{1}'.format(path, class_path)

    def _get_test_case_id(self, mark, part):
        parameters = part.get('parameters', None)
        parameterized = True
        selected_params = None
        if mark is not None:
            parameterized = mark.kwargs.get('parameterized', False)
            selected_params = mark.kwargs.get('params', None)
        if selected_params is not None and not isinstance(selected_params,
                                                          list):
            selected_params = [selected_params]

        param_str = None
        if parameterized and parameters is not None and len(parameters) > 0:
            if selected_params is not None and len(selected_params) > 0:
                param_list = [str(parameters.get(param, None)) for param in
                              selected_params]
            else:
                param_list = [str(param) for param in parameters.values()]
            param_str = '[{}]'.format(','.join(sorted(param_list)))

        name_part = part['code_ref']
        if mark is None:
            if param_str is None:
                return name_part
            else:
                return name_part + param_str
        else:
            if mark.args is not None and len(mark.args) > 0:
                name_part = str(mark.args[0])
            else:
                name_part = ""
            if param_str is None:
                return name_part
            else:
                return name_part + param_str

    def _get_issue_ids(self, mark):
        issue_ids = mark.kwargs.get("issue_id", [])
        if not isinstance(issue_ids, list):
            issue_ids = [issue_ids]
        return issue_ids

    def _get_issue_description_line(self, mark, default_url):
        issue_ids = self._get_issue_ids(mark)
        if not issue_ids:
            return mark.kwargs["reason"]

        mark_url = mark.kwargs.get("url", None) or default_url
        reason = mark.kwargs.get("reason", mark.name)
        issues = ""
        for issue_id in issue_ids:
            issue_url = mark_url.format(issue_id=issue_id) if \
                mark_url else None
            template = " [{issue_id}]({url})" if issue_url \
                else " {issue_id}"
            issues += template.format(issue_id=issue_id,
                                      url=issue_url)
        return "* {}:{}".format(reason, issues)

    def _get_issue(self, mark):
        """Add issues description and issue_type to the test item.

        :param mark: pytest mark
        """
        default_url = self._config.rp_issue_system_url
        issue_description_line = \
            self._get_issue_description_line(mark, default_url)

        # Set issue_type only for first issue mark
        issue_short_name = None
        if "issue_type" in mark.kwargs:
            issue_short_name = mark.kwargs["issue_type"]

        # default value
        issue_short_name = "TI" if issue_short_name is None else \
            issue_short_name

        registered_issues = self.issue_types
        if issue_short_name in registered_issues:
            return Issue(registered_issues[issue_short_name],
                         issue_description_line)

    def _to_attribute(self, attribute_tuple):
        if attribute_tuple[0]:
            return {'key': attribute_tuple[0], 'value': attribute_tuple[1]}
        else:
            return {'value': attribute_tuple[1]}

    def _get_parameters(self, item):
        """
        Get params of item.

        :param item: Pytest.Item
        :return: dict of params
        """
        return item.callspec.params if hasattr(item, 'callspec') else None

    def _process_attributes(self, part):
        """
        Process all types of attributes of item.

        :param part: item context
        """
        item = part['item']

        parameters = self._get_parameters(item)
        part['parameters'] = parameters

        code_ref = self._get_code_ref(item)
        part['code_ref'] = code_ref

        attributes = set()
        for marker in part['item'].iter_markers():
            if marker.name == 'tc_id':
                test_case_id = self._get_test_case_id(marker, part)
                part['test_case_id'] = test_case_id
                continue
            if marker.name == 'issue':
                issue = self._get_issue(marker)
                part['issue'] = issue
                if self._config.rp_issue_id_marks:
                    for issue_id in self._get_issue_ids(marker):
                        attributes.add((marker.name, issue_id))
                continue
            if marker.name in self._config.rp_ignore_attributes \
                    or marker.name in PYTEST_MARKS_IGNORE:
                continue
            if len(marker.args) > 0:
                attributes.add((marker.name, str(marker.args[0])))
            else:
                attributes.add((None, marker.name))

        part['attributes'] = [self._to_attribute(attribute)
                              for attribute in attributes]

        if 'test_case_id' not in part:
            part['test_case_id'] = self._get_test_case_id(None, part)

    def _build_start_step_rq(self, part):
        payload = {
            'attributes': part.get('attributes', None),
            'name': self._get_item_name(part['name']),
            'description': self._get_item_description(part['item']),
            'start_time': timestamp(),
            'item_type': 'STEP',
            'code_ref': part.get('code_ref', None),
            'parameters': part.get('parameters', None),
            'parent_item_id': self._lock(part['parent'],
                                         lambda p: p['item_id']),
            'test_case_id': part.get('test_case_id', None)
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
        self._process_attributes(current_part)
        item_id = self._start_step(self._build_start_step_rq(current_part))
        current_part['item_id'] = item_id
        current_part['exec'] = ExecStatus.IN_PROGRESS

    def process_results(self, test_item, report):
        """
        Save test item results after execution.

        :param test_item: pytest.Item
        :param report:    pytest's result report
        """
        if report.longrepr:
            self.post_log(test_item, report.longreprtext, loglevel='ERROR')

        node = self._item_parts[test_item][-1]
        # Defining test result
        if report.when == 'setup':
            node['status'] = 'PASSED'

        if report.failed:
            node['status'] = 'FAILED'
            return

        if report.skipped:
            if node['status'] in (None, 'PASSED'):
                node['status'] = 'SKIPPED'

    def _build_finish_step_rq(self, part):
        issue = part.get('issue', None)
        status = part['status']
        if status == 'SKIPPED' and not self._config.rp_is_skipped_an_issue:
            issue = NOT_ISSUE
        if status == 'PASSED':
            issue = None
        payload = {
            'end_time': timestamp(),
            'status': status,
            'issue': issue,
            'item_id': part['item_id']
        }
        return payload

    def _finish_step(self, finish_rq):
        log.debug('ReportPortal - Finish TestItem: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _finish_suite(self, finish_rq):
        log.debug('ReportPortal - End TestSuite: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _build_finish_suite_rq(self, part):
        payload = {
            'end_time': timestamp(),
            'item_id': part['item_id']
        }
        return payload

    def _proceed_suite_finish(self, part):
        if part.get('exec', ExecStatus.FINISHED) == ExecStatus.FINISHED:
            return

        self._finish_suite(self._build_finish_suite_rq(part))
        part['exec'] = ExecStatus.FINISHED

    def _finish_parents(self, part):
        if part['parent'].get('exec', ExecStatus.FINISHED) == \
                ExecStatus.FINISHED:
            return

        for item, child_part in part['parent']['children'].items():
            current_status = child_part['exec']
            if current_status != ExecStatus.FINISHED:
                current_status = self._lock(child_part, lambda p: p['exec'])
                if current_status != ExecStatus.FINISHED:
                    return

        self._lock(part['parent'], lambda p: self._proceed_suite_finish(p))
        self._finish_parents(part['parent'])

    def finish_pytest_item(self, test_item):
        """
        Finish pytest_item.

        :param test_item: pytest.Item
        :return: None
        """
        if self.rp is None:
            return

        parts = self._item_parts[test_item]
        item_part = parts[-1]
        self._finish_step(self._build_finish_step_rq(item_part))
        item_part['exec'] = ExecStatus.FINISHED
        self._finish_parents(item_part)

    def _get_items(self, exec_status):
        return [k for k, v in self._item_parts.items() if
                v[-1]['exec'] == exec_status]

    def finish_suites(self):
        """
        Finish all suites in run with status calculations.

        If an execution passes in multiprocessing mode we don't know which and
        how many items will be passed to our process. Because of that we don't
        finish suites until the very last step. And after that we finish them
        at once.
        """
        # Ensure there is no running items
        while len(self._get_items(ExecStatus.IN_PROGRESS)) > 0:
            sleep(0.1)
        skipped_items = self._get_items(ExecStatus.CREATED)
        for item in skipped_items:
            parts = list(self._item_parts[item])
            parts.reverse()
            for part in parts[1:-1]:
                if part['exec'] == ExecStatus.IN_PROGRESS:
                    self._lock(part, lambda p: self._proceed_suite_finish(p))

    def _build_finish_launch_rq(self):
        finish_rq = {
            'end_time': timestamp()
        }
        return finish_rq

    def _finish_launch(self, finish_rq):
        log.debug('ReportPortal - Finish launch: request_body=%s', finish_rq)
        self.rp.finish_launch(**finish_rq)

    def finish_launch(self):
        """
        Finish tests launch.

        :return: None
        """
        if self.rp is None:
            return

        # To finish launch session str parameter is needed
        self._finish_launch(self._build_finish_launch_rq())

    def post_log(self, test_item, message, loglevel='INFO', attachment=None):
        """
        Send a log message to the Report Portal.

        :param test_item: pytest.Item
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
        item_id = self._item_parts[test_item][-1]['item_id']
        sl_rq = {
            'item_id': item_id,
            'time': timestamp(),
            'message': message,
            'level': loglevel,
            'attachment': attachment
        }
        self.rp.log(**sl_rq)

    def start(self):
        """
        Start servicing Report Portal requests.
        """
        if self.rp is None:
            self.parent_item_id = self._config.rp_parent_item_id
            self.ignored_attributes = list(
                set(
                    self._config.rp_ignore_attributes or []
                ).union({'parametrize'})
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
        else:
            log.debug('The Report Portal is already initialized')
        self.rp.start()

    def stop(self):
        """
        Finish servicing Report Portal requests.
        """

        self.rp.terminate()
        self.rp = None
