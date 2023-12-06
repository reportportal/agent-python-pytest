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

"""This module includes Service functions for work with pytest agent."""

import logging
import os.path
import sys
import threading
from functools import wraps
from os import curdir
from time import time, sleep
from typing import List, Any, Optional, Set, Dict, Tuple, Union

from _pytest.doctest import DoctestItem
from aenum import auto, Enum, unique
from pytest import Class, Function, Module, Package, Item, Session, \
    PytestWarning
from reportportal_client.core.rp_issues import Issue, ExternalIssue
from reportportal_client.aio import Task

from .config import AgentConfig

try:
    from pytest import Instance
except ImportError:
    # in pytest >= 7.0 this type was removed
    Instance = type('dummy', (), {})
from reportportal_client import RP, create_client
from reportportal_client.helpers import (
    dict_to_payload,
    gen_attributes,
    get_launch_sys_attrs,
    get_package_version
)

log = logging.getLogger(__name__)

MAX_ITEM_NAME_LENGTH: int = 256
TRUNCATION_STR: str = '...'
ROOT_DIR: str = str(os.path.abspath(curdir))
PYTEST_MARKS_IGNORE: Set[str] = {'parametrize', 'usefixtures',
                                 'filterwarnings'}
NOT_ISSUE: Issue = Issue('NOT_ISSUE')
ISSUE_DESCRIPTION_LINE_TEMPLATE: str = '* {}:{}'
ISSUE_DESCRIPTION_URL_TEMPLATE: str = ' [{issue_id}]({url})'
ISSUE_DESCRIPTION_ID_TEMPLATE: str = ' {issue_id}'


def timestamp():
    """Time for difference between start and finish tests."""
    return str(int(time() * 1000))


def trim_docstring(docstring: str) -> str:
    """
    Convert docstring.

    :param docstring: input docstring
    :return: trimmed docstring
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


def check_rp_enabled(func):
    """Verify is RP is enabled in config."""

    @wraps(func)
    def wrap(*args, **kwargs):
        if args and isinstance(args[0], PyTestServiceClass):
            if not args[0].rp:
                return
        func(*args, **kwargs)

    return wrap


class PyTestServiceClass:
    """Pytest service class for reporting test results to the Report Portal."""

    _config: AgentConfig
    _issue_types: Dict[str, str]
    _tree_path: Dict[Item, List[Dict[str, Any]]]
    _log_levels: Tuple[str, str, str, str, str]
    _start_tracker: Set[str]
    _launch_id: Optional[str]
    agent_name: str
    agent_version: str
    ignored_attributes: List[str]
    parent_item_id: Optional[str]
    rp: Optional[RP]
    project_settings: Union[Dict[str, Any], Task]

    def __init__(self, agent_config: AgentConfig) -> None:
        """Initialize instance attributes."""
        self._config = agent_config
        self._issue_types = {}
        self._tree_path = {}
        self._log_levels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')
        self._start_tracker = set()
        self._launch_id = None
        self.agent_name = 'pytest-reportportal'
        self.agent_version = get_package_version(self.agent_name)
        self.ignored_attributes = []
        self.parent_item_id = None
        self.rp = None
        self.project_settings = {}

    @property
    def issue_types(self) -> Dict[str, str]:
        """Issue types for the Report Portal project."""
        if self._issue_types:
            return self._issue_types
        if not self.project_settings:
            return self._issue_types
        project_settings = self.project_settings
        if not isinstance(self.project_settings, dict):
            project_settings = project_settings.blocking_result()
        for values in project_settings["subTypes"].values():
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
            '{}|{}'.format(self.agent_name, self.agent_version))
        return attributes + dict_to_payload(system_attributes)

    def _build_start_launch_rq(self):
        rp_launch_attributes = self._config.rp_launch_attributes
        attributes = gen_attributes(rp_launch_attributes) if rp_launch_attributes else None

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

    @check_rp_enabled
    def start_launch(self) -> Optional[str]:
        """
        Launch test items.

        :return: item ID
        """
        sl_pt = self._build_start_launch_rq()
        log.debug('ReportPortal - Start launch: request_body=%s', sl_pt)
        self._launch_id = self.rp.start_launch(**sl_pt)
        log.debug('ReportPortal - Launch started: id=%s', self._launch_id)
        return self._launch_id

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

    def _get_tree_path(self, item):
        """
        Get item of parents.

        :param item: pytest.Item
        :return list of parents
        """
        path = [item]
        parent = item.parent
        while parent is not None and not isinstance(parent, Session):
            if not isinstance(parent, Instance):
                path.append(parent)
            parent = parent.parent

        path.reverse()
        return path

    def _get_leaf(self, leaf_type, parent_item, item, item_id=None):
        """Construct a leaf for the itest tree.

        :param leaf_type:   the leaf type
        :param parent_item: parent pytest.Item of the current leaf
        :param item:        leaf's pytest.Item
        :return: a leaf
        """
        return {
            'children': {}, 'type': leaf_type, 'item': item,
            'parent': parent_item, 'lock': threading.Lock(),
            'exec': ExecStatus.CREATED, 'item_id': item_id
        }

    def _build_test_tree(self, session):
        """Construct a tree of tests and their suites.

        :param session: pytest.Session object of the current execution
        :return: a tree of all tests and their suites
        """
        test_tree = self._get_leaf(LeafType.ROOT, None, None,
                                   item_id=self.parent_item_id)

        for item in session.items:
            dir_path = self._get_item_dirs(item)
            class_path = self._get_tree_path(item)

            current_leaf = test_tree
            for i, leaf in enumerate(dir_path + class_path):
                children_leafs = current_leaf['children']

                leaf_type = LeafType.DIR
                if i >= len(dir_path):
                    leaf_type = LeafType.CODE

                if leaf not in children_leafs:
                    children_leafs[leaf] = self._get_leaf(leaf_type,
                                                          current_leaf,
                                                          leaf)
                current_leaf = children_leafs[leaf]
        return test_tree

    def _remove_root_package(self, test_tree):
        if test_tree['type'] == LeafType.ROOT or \
                test_tree['type'] == LeafType.DIR:
            for item, child_leaf in test_tree['children'].items():
                self._remove_root_package(child_leaf)
                return
        if test_tree['type'] == LeafType.CODE and \
                isinstance(test_tree['item'], Package) and \
                test_tree['parent']['type'] == LeafType.DIR:
            parent_leaf = test_tree['parent']
            current_item = test_tree['item']
            del parent_leaf['children'][current_item]
            for item, child_leaf in test_tree['children'].items():
                parent_leaf['children'][item] = child_leaf
                child_leaf['parent'] = parent_leaf

    def _remove_root_dirs(self, test_tree, max_dir_level, dir_level=0):
        if test_tree['type'] == LeafType.ROOT:
            for item, child_leaf in test_tree['children'].items():
                self._remove_root_dirs(child_leaf, max_dir_level, 1)
                return
        if test_tree['type'] == LeafType.DIR and dir_level <= max_dir_level:
            new_level = dir_level + 1
            parent_leaf = test_tree['parent']
            current_item = test_tree['item']
            del parent_leaf['children'][current_item]
            for item, child_leaf in test_tree['children'].items():
                parent_leaf['children'][item] = child_leaf
                child_leaf['parent'] = parent_leaf
                self._remove_root_dirs(child_leaf, max_dir_level,
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

        for item, child_leaf in test_tree['children'].items():
            self._generate_names(child_leaf)

    def _merge_leaf_type(self, test_tree, leaf_type, separator):
        child_items = list(test_tree['children'].items())
        if test_tree['type'] != leaf_type:
            for item, child_leaf in child_items:
                self._merge_leaf_type(child_leaf, leaf_type, separator)
        elif len(test_tree['children'].items()) > 0:
            parent_leaf = test_tree['parent']
            current_item = test_tree['item']
            current_name = test_tree['name']
            del parent_leaf['children'][current_item]
            for item, child_leaf in child_items:
                parent_leaf['children'][item] = child_leaf
                child_leaf['parent'] = parent_leaf
                child_leaf['name'] = \
                    current_name + separator + child_leaf['name']
                self._merge_leaf_type(child_leaf, leaf_type, separator)

    def _merge_dirs(self, test_tree):
        self._merge_leaf_type(test_tree, LeafType.DIR,
                              self._config.rp_dir_path_separator)

    def _merge_code(self, test_tree):
        self._merge_leaf_type(test_tree, LeafType.CODE, '::')

    def _build_item_paths(self, leaf, path):
        if 'children' in leaf and len(leaf['children']) > 0:
            path.append(leaf)
            for name, child_leaf in leaf['children'].items():
                self._build_item_paths(child_leaf, path)
            path.pop()
        elif leaf['type'] != LeafType.ROOT:
            self._tree_path[leaf['item']] = path + [leaf]

    @check_rp_enabled
    def collect_tests(self, session):
        """
        Collect all tests.

        :param session: pytest.Session
        """
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
                    'Test leaf ID was truncated to "{}" because of name size '
                    'constrains on Report Portal'.format(name)
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

    def _lock(self, leaf, func):
        """
        Lock test tree leaf and execute a function, bypass the leaf to it.

        :param leaf: a leaf to lock
        :param func: a function to execute
        :return: the result of the function bypassed
        """
        if 'lock' in leaf:
            with leaf['lock']:
                return func(leaf)
        return func(leaf)

    def _build_start_suite_rq(self, leaf):
        code_ref = str(leaf['item']) if leaf['type'] == LeafType.DIR \
            else str(leaf['item'].fspath)
        payload = {
            'name': self._get_item_name(leaf['name']),
            'description': self._get_item_description(leaf['item']),
            'start_time': timestamp(),
            'item_type': 'SUITE',
            'code_ref': code_ref,
            'parent_item_id': self._lock(leaf['parent'],
                                         lambda p: p['item_id'])
        }
        return payload

    def _start_suite(self, suite_rq):
        log.debug('ReportPortal - Start Suite: request_body=%s',
                  suite_rq)
        return self.rp.start_test_item(**suite_rq)

    def _create_suite(self, leaf):
        if leaf['exec'] != ExecStatus.CREATED:
            return
        item_id = self._start_suite(self._build_start_suite_rq(leaf))
        leaf['item_id'] = item_id
        leaf['exec'] = ExecStatus.IN_PROGRESS

    @check_rp_enabled
    def _create_suite_path(self, item):
        path = self._tree_path[item]
        for leaf in path[1:-1]:
            if leaf['exec'] != ExecStatus.CREATED:
                continue
            self._lock(leaf, lambda p: self._create_suite(p))

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

    def _get_test_case_id(self, mark, leaf):
        parameters = leaf.get('parameters', None)
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

        basic_name_part = leaf['code_ref']
        if mark is None:
            if param_str is None:
                return basic_name_part
            else:
                return basic_name_part + param_str
        else:
            if mark.args is not None and len(mark.args) > 0:
                basic_name_part = str(mark.args[0])
            else:
                basic_name_part = ""
            if param_str is None:
                return basic_name_part
            else:
                return basic_name_part + param_str

    def _get_issue_ids(self, mark):
        issue_ids = mark.kwargs.get("issue_id", [])
        if not isinstance(issue_ids, List):
            issue_ids = [issue_ids]
        return issue_ids

    def _get_issue_urls(self, mark, default_url):
        issue_ids = self._get_issue_ids(mark)
        if not issue_ids:
            return None
        mark_url = mark.kwargs.get("url", None) or default_url
        return [mark_url.format(issue_id=issue_id) if mark_url else None
                for issue_id in issue_ids]

    def _get_issue_description_line(self, mark, default_url):
        issue_ids = self._get_issue_ids(mark)
        if not issue_ids:
            return mark.kwargs["reason"]

        issue_urls = self._get_issue_urls(mark, default_url)
        reason = mark.kwargs.get("reason", mark.name)
        issues = ""
        for i, issue_id in enumerate(issue_ids):
            issue_url = issue_urls[i]
            template = ISSUE_DESCRIPTION_URL_TEMPLATE if issue_url \
                else ISSUE_DESCRIPTION_ID_TEMPLATE
            issues += template.format(issue_id=issue_id,
                                      url=issue_url)
        return ISSUE_DESCRIPTION_LINE_TEMPLATE.format(reason, issues)

    def _get_issue(self, mark):
        """Add issues description and issue_type to the test item.

        :param mark: pytest mark
        :return: Issue object
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
        issue = None
        if issue_short_name in registered_issues:
            issue = Issue(registered_issues[issue_short_name],
                          issue_description_line)

        if issue and self._config.rp_bts_project and self._config.rp_bts_url:
            issue_ids = self._get_issue_ids(mark)
            issue_urls = self._get_issue_urls(mark, default_url)
            for issue_id, issue_url in zip(issue_ids, issue_urls):
                issue.external_issue_add(
                    ExternalIssue(bts_url=self._config.rp_bts_url,
                                  bts_project=self._config.rp_bts_project,
                                  ticket_id=issue_id, url=issue_url)
                )
        return issue

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

    def _process_test_case_id(self, leaf):
        """
        Process Test Case ID if set.

        :param leaf: item context
        :return: Test Case ID string
        """
        tc_ids = [m for m in leaf['item'].iter_markers() if m.name == 'tc_id']
        if len(tc_ids) > 0:
            return self._get_test_case_id(tc_ids[0], leaf)
        return self._get_test_case_id(None, leaf)

    def _process_issue(self, item):
        """
        Process Issue if set.

        :param item: Pytest.Item
        :return: Issue
        """
        issues = [m for m in item.iter_markers() if m.name == 'issue']
        if len(issues) > 0:
            return self._get_issue(issues[0])

    def _process_attributes(self, item):
        """
        Process attributes of item.

        :param item: Pytest.Item
        :return: a set of attributes
        """
        attributes = set()
        for marker in item.iter_markers():
            if marker.name == 'issue':
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

        return [self._to_attribute(attribute)
                for attribute in attributes]

    def _process_metadata_item_start(self, leaf):
        """
        Process all types of item metadata for its start event.

        :param leaf: item context
        """
        item = leaf['item']
        leaf['parameters'] = self._get_parameters(item)
        leaf['code_ref'] = self._get_code_ref(item)
        leaf['test_case_id'] = self._process_test_case_id(leaf)
        leaf['issue'] = self._process_issue(item)
        leaf['attributes'] = self._process_attributes(item)

    def _process_metadata_item_finish(self, leaf):
        """
        Process all types of item metadata for its finish event.

        :param leaf: item context
        """
        item = leaf['item']
        leaf['attributes'] = self._process_attributes(item)
        leaf['issue'] = self._process_issue(item)

    def _build_start_step_rq(self, leaf):
        payload = {
            'attributes': leaf.get('attributes', None),
            'name': self._get_item_name(leaf['name']),
            'description': self._get_item_description(leaf['item']),
            'start_time': timestamp(),
            'item_type': 'STEP',
            'code_ref': leaf.get('code_ref', None),
            'parameters': leaf.get('parameters', None),
            'parent_item_id': self._lock(leaf['parent'],
                                         lambda p: p['item_id']),
            'test_case_id': leaf.get('test_case_id', None)
        }
        return payload

    def _start_step(self, step_rq):
        log.debug('ReportPortal - Start TestItem: request_body=%s', step_rq)
        return self.rp.start_test_item(**step_rq)

    def __unique_id(self):
        return str(os.getpid()) + '-' + str(threading.current_thread().ident)

    def __started(self):
        return self.__unique_id() in self._start_tracker

    @check_rp_enabled
    def start_pytest_item(self, test_item=None):
        """
        Start pytest_item.

        :param test_item: pytest.Item
        :return: item ID
        """
        if test_item is None:
            return

        if not self.__started():
            self.start()

        self._create_suite_path(test_item)

        # Item type should be sent as "STEP" until we upgrade to RPv6.
        # Details at:
        # https://github.com/reportportal/agent-Python-RobotFramework/issues/56
        current_leaf = self._tree_path[test_item][-1]
        self._process_metadata_item_start(current_leaf)
        item_id = self._start_step(self._build_start_step_rq(current_leaf))
        current_leaf['item_id'] = item_id
        current_leaf['exec'] = ExecStatus.IN_PROGRESS

    def process_results(self, test_item, report):
        """
        Save test item results after execution.

        :param test_item: pytest.Item
        :param report:    pytest's result report
        """
        if report.longrepr:
            self.post_log(test_item, report.longreprtext, log_level='ERROR')

        leaf = self._tree_path[test_item][-1]
        # Defining test result
        if report.when == 'setup':
            leaf['status'] = 'PASSED'

        if report.failed:
            leaf['status'] = 'FAILED'
            return

        if report.skipped:
            if leaf['status'] in (None, 'PASSED'):
                leaf['status'] = 'SKIPPED'

    def _build_finish_step_rq(self, leaf):
        issue = leaf.get('issue', None)
        status = leaf['status']
        if status == 'SKIPPED' and not self._config.rp_is_skipped_an_issue:
            issue = NOT_ISSUE
        if status == 'PASSED':
            issue = None
        payload = {
            'attributes': leaf.get('attributes', None),
            'end_time': timestamp(),
            'status': status,
            'issue': issue,
            'item_id': leaf['item_id']
        }
        return payload

    def _finish_step(self, finish_rq):
        log.debug('ReportPortal - Finish TestItem: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _finish_suite(self, finish_rq):
        log.debug('ReportPortal - End TestSuite: request_body=%s', finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _build_finish_suite_rq(self, leaf):
        payload = {
            'end_time': timestamp(),
            'item_id': leaf['item_id']
        }
        return payload

    def _proceed_suite_finish(self, leaf):
        if leaf.get('exec', ExecStatus.FINISHED) == ExecStatus.FINISHED:
            return

        self._finish_suite(self._build_finish_suite_rq(leaf))
        leaf['exec'] = ExecStatus.FINISHED

    def _finish_parents(self, leaf):
        if 'parent' not in leaf or leaf['parent'] is None \
                or leaf['parent']['type'] is LeafType.ROOT \
                or leaf['parent'].get('exec', ExecStatus.FINISHED) == \
                ExecStatus.FINISHED:
            return

        for item, child_leaf in leaf['parent']['children'].items():
            current_status = child_leaf['exec']
            if current_status != ExecStatus.FINISHED:
                current_status = self._lock(child_leaf, lambda p: p['exec'])
                if current_status != ExecStatus.FINISHED:
                    return

        self._lock(leaf['parent'], lambda p: self._proceed_suite_finish(p))
        self._finish_parents(leaf['parent'])

    @check_rp_enabled
    def finish_pytest_item(self, test_item):
        """
        Finish pytest_item.

        :param test_item: pytest.Item
        :return: None
        """
        path = self._tree_path[test_item]
        leaf = path[-1]
        self._process_metadata_item_finish(leaf)
        self._finish_step(self._build_finish_step_rq(leaf))
        leaf['exec'] = ExecStatus.FINISHED
        self._finish_parents(leaf)

    def _get_items(self, exec_status):
        return [k for k, v in self._tree_path.items() if
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
        finish_time = time()
        while len(self._get_items(ExecStatus.IN_PROGRESS)) > 0 \
                and time() - finish_time <= self._config.rp_launch_timeout:
            sleep(0.1)
        skipped_items = self._get_items(ExecStatus.CREATED)
        for item in skipped_items:
            path = list(self._tree_path[item])
            path.reverse()
            for leaf in path[1:-1]:
                if leaf['exec'] == ExecStatus.IN_PROGRESS:
                    self._lock(leaf, lambda p: self._proceed_suite_finish(p))

    def _build_finish_launch_rq(self):
        finish_rq = {
            'end_time': timestamp()
        }
        return finish_rq

    def _finish_launch(self, finish_rq):
        log.debug('ReportPortal - Finish launch: request_body=%s', finish_rq)
        self.rp.finish_launch(**finish_rq)

    @check_rp_enabled
    def finish_launch(self):
        """
        Finish tests launch.

        :return: None
        """
        # To finish launch session str parameter is needed
        self._finish_launch(self._build_finish_launch_rq())

    @check_rp_enabled
    def post_log(self, test_item, message, log_level='INFO', attachment=None):
        """
        Send a log message to the Report Portal.

        :param test_item: pytest.Item
        :param message:    message in log body
        :param log_level:   a level of a log entry (ERROR, WARN, INFO, DEBUG,
        TRACE, FATAL, UNKNOWN)
        :param attachment: attachment file
        :return: None
        """
        if log_level not in self._log_levels:
            log.warning('Incorrect loglevel = %s. Force set to INFO. '
                        'Available levels: %s.', log_level, self._log_levels)
        item_id = self._tree_path[test_item][-1]['item_id']
        sl_rq = {
            'item_id': item_id,
            'time': timestamp(),
            'message': message,
            'level': log_level,
            'attachment': attachment
        }
        self.rp.log(**sl_rq)

    def start(self) -> None:
        """Start servicing Report Portal requests."""
        self.parent_item_id = self._config.rp_parent_item_id
        self.ignored_attributes = list(
            set(
                self._config.rp_ignore_attributes or []
            ).union({'parametrize'})
        )
        log.debug('ReportPortal - Init service: endpoint=%s, '
                  'project=%s, api_key=%s', self._config.rp_endpoint,
                  self._config.rp_project, self._config.rp_api_key)
        launch_id = self._launch_id
        if self._config.rp_launch_id:
            launch_id = self._config.rp_launch_id
        self.rp = create_client(
            client_type=self._config.rp_client_type,
            endpoint=self._config.rp_endpoint,
            project=self._config.rp_project,
            api_key=self._config.rp_api_key,
            is_skipped_an_issue=self._config.rp_is_skipped_an_issue,
            log_batch_size=self._config.rp_log_batch_size,
            retries=self._config.rp_api_retries,
            verify_ssl=self._config.rp_verify_ssl,
            launch_uuid=launch_id,
            log_batch_payload_size=self._config.rp_log_batch_payload_size,
            launch_uuid_print=self._config.rp_launch_uuid_print,
            print_output=self._config.rp_launch_uuid_print_output,
            http_timeout=self._config.rp_http_timeout
        )
        if hasattr(self.rp, "get_project_settings"):
            self.project_settings = self.rp.get_project_settings()
        # noinspection PyUnresolvedReferences
        self._start_tracker.add(self.__unique_id())

    def stop(self):
        """Finish servicing Report Portal requests."""
        self.rp.close()
        self.rp = None
        self._start_tracker.remove(self.__unique_id())
