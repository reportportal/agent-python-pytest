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
import re
import sys
import threading
import traceback
from collections import OrderedDict
from functools import wraps
from os import curdir
from time import sleep, time
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Union

from _pytest.doctest import DoctestItem
from aenum import Enum, auto, unique
from py.path import local
from pytest import Class, Function, Item, Module, Package, PytestWarning, Session
from reportportal_client.aio import Task
from reportportal_client.core.rp_issues import ExternalIssue, Issue
from reportportal_client.helpers import markdown_helpers, timestamp

from .config import AgentConfig

try:
    # noinspection PyProtectedMember
    from pytest import Instance
except ImportError:
    # in pytest >= 7.0 this type was removed
    Instance = type("dummy", (), {})
try:
    from pytest import Dir
except ImportError:
    # in pytest < 8.0 there is no such type
    Dir = type("dummy", (), {})
try:
    from pytest import Mark
except ImportError:
    # in old pytest marks are located in the _pytest.mark module
    from _pytest.mark import Mark
try:
    # noinspection PyPackageRequirements
    from pytest_bdd.parser import Background, Feature, Scenario, ScenarioTemplate, Step

    # noinspection PyPackageRequirements
    from pytest_bdd.scenario import make_python_name

    PYTEST_BDD = True
except ImportError:
    Background = type("dummy", (), {})
    Feature = type("dummy", (), {})
    Scenario = type("dummy", (), {})
    ScenarioTemplate = type("dummy", (), {})
    Step = type("dummy", (), {})
    make_python_name: Callable[[str], str] = lambda x: x
    PYTEST_BDD = False

try:
    # noinspection PyPackageRequirements
    from pytest_bdd.parser import Rule
except ImportError:
    Rule = type("dummy", (), {})  # Old pytest-bdd versions do not have Rule

from reportportal_client import RP, create_client
from reportportal_client.helpers import dict_to_payload, gen_attributes, get_launch_sys_attrs, get_package_version

LOGGER = logging.getLogger(__name__)

KNOWN_LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR")
MAX_ITEM_NAME_LENGTH: int = 1024
TRUNCATION_STR: str = "..."
ROOT_DIR: str = str(os.path.abspath(curdir))
PYTEST_MARKS_IGNORE: Set[str] = {"parametrize", "usefixtures", "filterwarnings"}
NOT_ISSUE: Issue = Issue("NOT_ISSUE")
ISSUE_DESCRIPTION_LINE_TEMPLATE: str = "* {}:{}"
ISSUE_DESCRIPTION_URL_TEMPLATE: str = " [{issue_id}]({url})"
ISSUE_DESCRIPTION_ID_TEMPLATE: str = " {issue_id}"
PYTHON_REPLACE_REGEX = re.compile(r"\W")
ALPHA_REGEX = re.compile(r"^\d+_*")
BACKGROUND_STEP_NAME = "Background"


def trim_docstring(docstring: str) -> str:
    """
    Convert docstring.

    :param docstring: input docstring
    :return: trimmed docstring
    """
    if not docstring:
        return ""
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
    return "\n".join(trimmed)


@unique
class LeafType(Enum):
    """This class stores test item path types."""

    DIR = auto()
    FILE = auto()
    CODE = auto()
    ROOT = auto()
    SUITE = auto()
    NESTED = auto()


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
        if args and isinstance(args[0], PyTestService):
            if not args[0].rp:
                return
        return func(*args, **kwargs)

    return wrap


class PyTestService:
    """Pytest service class for reporting test results to the Report Portal."""

    _config: AgentConfig
    _issue_types: Dict[str, str]
    _tree_path: Dict[Any, List[Dict[str, Any]]]
    _bdd_tree: Optional[Dict[str, Any]]
    _bdd_item_by_name: Dict[str, Item]
    _bdd_scenario_by_item: Dict[Item, Scenario]
    _bdd_item_by_scenario: Dict[Scenario, Item]
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
        self._bdd_tree = None
        self._bdd_item_by_name = OrderedDict()
        self._bdd_scenario_by_item = {}
        self._bdd_item_by_scenario = {}
        self._start_tracker = set()
        self._launch_id = None
        self.agent_name = "pytest-reportportal"
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
        if not project_settings:
            return self._issue_types
        for values in project_settings["subTypes"].values():
            for item in values:
                self._issue_types[item["shortName"]] = item["locator"]
        return self._issue_types

    def _get_launch_attributes(self, ini_attrs: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Generate launch attributes in the format supported by the client.

        :param list ini_attrs: List for attributes from the pytest.ini file
        """
        attributes = ini_attrs or []
        system_attributes = get_launch_sys_attrs()
        system_attributes["agent"] = "{}|{}".format(self.agent_name, self.agent_version)
        return attributes + dict_to_payload(system_attributes)

    def _build_start_launch_rq(self) -> Dict[str, Any]:
        rp_launch_attributes = self._config.rp_launch_attributes
        attributes = gen_attributes(rp_launch_attributes) if rp_launch_attributes else None

        start_rq = {
            "attributes": self._get_launch_attributes(attributes),
            "name": self._config.rp_launch,
            "start_time": timestamp(),
            "description": self._config.rp_launch_description,
            "rerun": self._config.rp_rerun,
            "rerun_of": self._config.rp_rerun_of,
        }
        return start_rq

    @check_rp_enabled
    def start_launch(self) -> Optional[str]:
        """
        Launch test items.

        :return: item ID
        """
        sl_pt = self._build_start_launch_rq()
        LOGGER.debug("ReportPortal - Start launch: request_body=%s", sl_pt)
        self._launch_id = self.rp.start_launch(**sl_pt)
        LOGGER.debug("ReportPortal - Launch started: id=%s", self._launch_id)
        return self._launch_id

    def _get_item_dirs(self, item: Item) -> List[local]:
        """
        Get directory of item.

        :param item: pytest.Item
        :return: list of dirs
        """
        root_path = item.session.config.rootdir.strpath
        dir_path = item.fspath.new(basename="")
        rel_dir = dir_path.new(dirname=dir_path.relto(root_path), basename="", drive="")
        return [d for d in rel_dir.parts(reverse=False) if d.basename]

    def _get_tree_path(self, item: Item) -> List[Item]:
        """Get item of parents.

        :param item: pytest.Item
        :return list of parents
        """
        path = [item]
        parent = item.parent
        while parent is not None and not isinstance(parent, Session):
            if not isinstance(parent, Instance) and not isinstance(parent, Dir) and not isinstance(parent, Package):
                path.append(parent)
            parent = parent.parent

        path.reverse()
        return path

    def _create_leaf(
        self, leaf_type, parent_item: Optional[Dict[str, Any]], item: Optional[Any], item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Construct a leaf for the itest tree.

        :param leaf_type:   the leaf type
        :param parent_item: parent pytest.Item of the current leaf
        :param item:        the leaf's pytest.Item
        :return: a leaf
        """
        return {
            "children": {},
            "type": leaf_type,
            "item": item,
            "parent": parent_item,
            "lock": threading.Lock(),
            "exec": ExecStatus.CREATED,
            "item_id": item_id,
        }

    def _build_test_tree(self, session: Session) -> Dict[str, Any]:
        """Construct a tree of tests and their suites.

        :param session: pytest.Session object of the current execution
        :return: a tree of all tests and their suites
        """
        test_tree = self._create_leaf(LeafType.ROOT, None, None, item_id=self.parent_item_id)

        for item in session.items:
            dir_path = self._get_item_dirs(item)
            class_path = self._get_tree_path(item)

            current_leaf = test_tree
            for i, leaf in enumerate(dir_path + class_path):
                children_leafs = current_leaf["children"]

                leaf_type = LeafType.DIR
                if i == len(dir_path):
                    leaf_type = LeafType.FILE
                if i > len(dir_path):
                    leaf_type = LeafType.CODE

                if leaf not in children_leafs:
                    children_leafs[leaf] = self._create_leaf(leaf_type, current_leaf, leaf)
                current_leaf = children_leafs[leaf]
        return test_tree

    def _remove_root_dirs(self, test_tree: Dict[str, Any], max_dir_level: int, dir_level: int = 0) -> None:
        if test_tree["type"] == LeafType.ROOT:
            items = list(test_tree["children"].items())
            for item, child_leaf in items:
                self._remove_root_dirs(child_leaf, max_dir_level, 1)
            return
        if test_tree["type"] == LeafType.DIR and dir_level <= max_dir_level:
            new_level = dir_level + 1
            parent_leaf = test_tree["parent"]
            current_item = test_tree["item"]
            del parent_leaf["children"][current_item]
            for item, child_leaf in test_tree["children"].items():
                parent_leaf["children"][item] = child_leaf
                child_leaf["parent"] = parent_leaf
                self._remove_root_dirs(child_leaf, max_dir_level, new_level)

    def _remove_file_names(self, test_tree: Dict[str, Any]) -> None:
        if test_tree["type"] != LeafType.FILE:
            items = list(test_tree["children"].items())
            for item, child_leaf in items:
                self._remove_file_names(child_leaf)
            return
        if not self._config.rp_hierarchy_test_file:
            parent_leaf = test_tree["parent"]
            current_item = test_tree["item"]
            del parent_leaf["children"][current_item]
            for item, child_leaf in test_tree["children"].items():
                parent_leaf["children"][item] = child_leaf
                child_leaf["parent"] = parent_leaf
                self._remove_file_names(child_leaf)

    def _get_scenario_template(self, scenario: Scenario) -> Optional[ScenarioTemplate]:
        line_num = scenario.line_number
        feature = scenario.feature
        scenario_template = None
        for template in feature.scenarios.values():
            if template.line_number == line_num:
                scenario_template = template
                break
        if scenario_template and isinstance(scenario_template, ScenarioTemplate):
            return scenario_template

    def _generate_names(self, test_tree: Dict[str, Any]) -> None:
        if test_tree["type"] == LeafType.ROOT:
            test_tree["name"] = "root"

        if test_tree["type"] == LeafType.DIR:
            test_tree["name"] = test_tree["item"].basename

        if test_tree["type"] in {LeafType.CODE, LeafType.FILE}:
            item = test_tree["item"]
            if isinstance(item, Module):
                test_tree["name"] = os.path.split(str(item.fspath))[1]
            elif isinstance(item, Feature):
                name = item.name if item.name else item.rel_filename
                keyword = getattr(item, "keyword", "Feature")
                test_tree["name"] = f"{keyword}: {name}"
            elif isinstance(item, Scenario):
                scenario_template = self._get_scenario_template(item)
                if scenario_template and scenario_template.templated:
                    keyword = getattr(item, "keyword", "Scenario Outline")
                else:
                    keyword = getattr(item, "keyword", "Scenario")
                test_tree["name"] = f"{keyword}: {item.name}"
            elif isinstance(item, Rule):
                keyword = getattr(item, "keyword", "Rule")
                test_tree["name"] = f"{keyword}: {item.name}"
            else:
                test_tree["name"] = item.name

        if test_tree["type"] == LeafType.SUITE:
            item = test_tree["item"]
            if isinstance(item, Rule):
                keyword = getattr(item, "keyword", "Rule")
                test_tree["name"] = f"{keyword}: {item.name}"

        for item, child_leaf in test_tree["children"].items():
            self._generate_names(child_leaf)

    def _merge_leaf_types(self, test_tree: Dict[str, Any], leaf_types: Set, separator: str) -> None:
        child_items = list(test_tree["children"].items())
        if test_tree["type"] not in leaf_types:
            for item, child_leaf in child_items:
                self._merge_leaf_types(child_leaf, leaf_types, separator)
        elif len(child_items) > 0:
            parent_leaf = test_tree["parent"]
            current_item = test_tree["item"]
            current_name = test_tree["name"]
            child_types = [child_leaf["type"] in leaf_types for _, child_leaf in child_items]
            if all(child_types):
                del parent_leaf["children"][current_item]
            for item, child_leaf in child_items:
                if all(child_types):
                    parent_leaf["children"][item] = child_leaf
                    child_leaf["parent"] = parent_leaf
                    child_leaf["name"] = current_name + separator + child_leaf["name"]
                self._merge_leaf_types(child_leaf, leaf_types, separator)

    def _merge_dirs(self, test_tree: Dict[str, Any]) -> None:
        self._merge_leaf_types(test_tree, {LeafType.DIR, LeafType.FILE}, self._config.rp_dir_path_separator)

    def _merge_code_with_separator(self, test_tree: Dict[str, Any], separator: str) -> None:
        self._merge_leaf_types(test_tree, {LeafType.CODE, LeafType.FILE, LeafType.DIR, LeafType.SUITE}, separator)

    def _merge_code(self, test_tree: Dict[str, Any]) -> None:
        self._merge_code_with_separator(test_tree, "::")

    def _build_item_paths(self, leaf: Dict[str, Any], path: List[Dict[str, Any]]) -> None:
        children = leaf.get("children", {})
        if PYTEST_BDD:
            all_background_steps = all([isinstance(child, Background) for child in children.keys()])
        else:
            all_background_steps = False
        if len(children) > 0 and not all_background_steps:
            path.append(leaf)
            for name, child_leaf in leaf["children"].items():
                self._build_item_paths(child_leaf, path)
            path.pop()
        elif leaf["type"] != LeafType.ROOT:
            self._tree_path[leaf["item"]] = path + [leaf]

    @check_rp_enabled
    def collect_tests(self, session: Session) -> None:
        """Collect all tests.

        :param session: pytest.Session
        """
        # Create a test tree to be able to apply mutations
        test_tree = self._build_test_tree(session)
        self._remove_root_dirs(test_tree, self._config.rp_dir_level)
        self._remove_file_names(test_tree)
        self._generate_names(test_tree)
        if not self._config.rp_hierarchy_dirs:
            self._merge_dirs(test_tree)
        if not self._config.rp_hierarchy_code:
            self._merge_code(test_tree)
        self._build_item_paths(test_tree, [])

    def _truncate_item_name(self, name: str) -> str:
        """Get name of item.

        :param name: Test Item name
        :return: truncated to maximum length name if needed
        """
        if len(name) > MAX_ITEM_NAME_LENGTH:
            name = name[: MAX_ITEM_NAME_LENGTH - len(TRUNCATION_STR)] + TRUNCATION_STR
            LOGGER.warning(
                PytestWarning(
                    f'Test leaf ID was truncated to "{name}" because of name size constrains on Report Portal'
                )
            )
        return name

    def _get_item_description(self, test_item: Any) -> Optional[str]:
        """Get description of item.

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
        if isinstance(test_item, (Feature, Rule)):
            description = test_item.description
            if description:
                return description.lstrip()  # There is a bug in pytest-bdd that adds an extra space

    def _lock(self, leaf: Dict[str, Any], func: Callable[[Dict[str, Any]], Any]) -> Any:
        """
        Lock test tree leaf and execute a function, bypass the leaf to it.

        :param leaf: a leaf to lock
        :param func: a function to execute
        :return: the result of the function bypassed
        """
        if "lock" in leaf:
            with leaf["lock"]:
                return func(leaf)
        return func(leaf)

    def _process_bdd_attributes(self, item: Union[Feature, Scenario, Rule]) -> List[Dict[str, str]]:
        tags = []
        tags.extend(item.tags)
        if isinstance(item, Scenario):
            test_attributes = self._config.rp_tests_attributes
            tags.extend(test_attributes if test_attributes else [])
            template = self._get_scenario_template(item)
            if template and template.templated:
                examples = []
                if isinstance(template.examples, list):
                    examples.extend(template.examples)
                else:
                    examples.append(template.examples)
                for example in examples:
                    tags.extend(getattr(example, "tags", []))
        return gen_attributes(tags)

    def _get_suite_code_ref(self, leaf: Dict[str, Any]) -> str:
        item = leaf["item"]
        if leaf["type"] == LeafType.DIR:
            code_ref = str(item)
        elif leaf["type"] == LeafType.FILE:
            if isinstance(item, Feature):
                code_ref = str(item.rel_filename)
            else:
                code_ref = str(item.fspath)
        elif leaf["type"] == LeafType.SUITE:
            code_ref = self._get_suite_code_ref(leaf["parent"]) + f"/[{type(item).__name__}:{item.name}]"
        else:
            code_ref = str(item.fspath)
        return code_ref

    def _build_start_suite_rq(self, leaf: Dict[str, Any]) -> Dict[str, Any]:
        code_ref = self._get_suite_code_ref(leaf)
        parent_item_id = self._lock(leaf["parent"], lambda p: p.get("item_id")) if "parent" in leaf else None
        item = leaf["item"]
        payload = {
            "name": self._truncate_item_name(leaf["name"]),
            "description": self._get_item_description(item),
            "start_time": timestamp(),
            "item_type": "SUITE",
            "code_ref": code_ref,
            "parent_item_id": parent_item_id,
        }
        if isinstance(item, (Feature, Scenario, Rule)):
            payload["attributes"] = self._process_bdd_attributes(item)
        return payload

    def _start_suite(self, suite_rq: Dict[str, Any]) -> Optional[str]:
        LOGGER.debug("ReportPortal - Start Suite: request_body=%s", suite_rq)
        return self.rp.start_test_item(**suite_rq)

    def _create_suite(self, leaf: Dict[str, Any]) -> None:
        if leaf["exec"] != ExecStatus.CREATED:
            return
        item_id = self._start_suite(self._build_start_suite_rq(leaf))
        leaf["item_id"] = item_id
        leaf["exec"] = ExecStatus.IN_PROGRESS

    @check_rp_enabled
    def _create_suite_path(self, item: Any) -> None:
        path = self._tree_path[item]
        for leaf in path[1:-1]:
            if leaf["exec"] != ExecStatus.CREATED:
                continue
            self._lock(leaf, lambda p: self._create_suite(p))

    def _get_item_name(self, mark) -> Optional[str]:
        return mark.kwargs.get("name", mark.args[0] if mark.args else None)

    def _get_code_ref(self, item: Item) -> str:
        # Generate script path from work dir, use only backslashes to have the
        # same path on different systems and do not affect Test Case ID on
        # different systems
        path = os.path.relpath(str(item.fspath), ROOT_DIR).replace("\\", "/")
        method_name = (
            item.originalname
            if hasattr(item, "originalname") and getattr(item, "originalname") is not None
            else item.name
        )
        parent = item.parent
        classes = [method_name]
        while not isinstance(parent, Module):
            if not isinstance(parent, Instance) and hasattr(parent, "name"):
                classes.append(parent.name)
            if hasattr(parent, "parent"):
                parent = parent.parent
            else:
                break
        classes.reverse()
        class_path = ".".join(classes)
        return "{0}:{1}".format(path, class_path)

    def _get_test_case_id(self, mark, leaf: Dict[str, Any]) -> str:
        parameters: Optional[Dict[str, Any]] = leaf.get("parameters", None)
        parameters_indices: Optional[Dict[str, Any]] = leaf.get("parameters_indices") or {}
        parameterized = True
        selected_params: Optional[List[str]] = None
        use_index = False
        if mark is not None:
            parameterized = mark.kwargs.get("parameterized", False)
            selected_params: Optional[Union[str, List[str]]] = mark.kwargs.get("params", None)
            use_index = mark.kwargs.get("use_index", False)
        if selected_params is not None and not isinstance(selected_params, list):
            selected_params = [selected_params]

        param_str = None
        if parameterized and parameters is not None and len(parameters) > 0:
            if selected_params is not None and len(selected_params) > 0:
                if use_index:
                    param_list = [str((param, parameters_indices.get(param, None))) for param in selected_params]
                else:
                    param_list = [str(parameters.get(param, None)) for param in selected_params]
            elif use_index:
                param_list = [str(param) for param in parameters_indices.items()]
            else:
                param_list = [str(param) for param in parameters.values()]
            param_str = "[{}]".format(",".join(sorted(param_list)))

        basic_name_part = leaf["code_ref"]
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
        return [mark_url.format(issue_id=issue_id) if mark_url else None for issue_id in issue_ids]

    def _get_issue_description_line(self, mark, default_url):
        issue_ids = self._get_issue_ids(mark)
        if not issue_ids:
            return mark.kwargs["reason"]

        issue_urls = self._get_issue_urls(mark, default_url)
        reason = mark.kwargs.get("reason", mark.name)
        issues = ""
        for i, issue_id in enumerate(issue_ids):
            issue_url = issue_urls[i]
            template = ISSUE_DESCRIPTION_URL_TEMPLATE if issue_url else ISSUE_DESCRIPTION_ID_TEMPLATE
            issues += template.format(issue_id=issue_id, url=issue_url)
        return ISSUE_DESCRIPTION_LINE_TEMPLATE.format(reason, issues)

    def _get_issue(self, mark: Mark) -> Optional[Issue]:
        """Add issues description and issue_type to the test item.

        :param mark: pytest mark
        :return: Issue object
        """
        default_url = self._config.rp_bts_issue_url

        issue_description_line = self._get_issue_description_line(mark, default_url)

        # Set issue_type only for first issue mark
        issue_short_name = None
        if "issue_type" in mark.kwargs:
            issue_short_name = mark.kwargs["issue_type"]

        # default value
        issue_short_name = "TI" if issue_short_name is None else issue_short_name

        registered_issues = self.issue_types
        issue = None
        if issue_short_name in registered_issues:
            issue = Issue(registered_issues[issue_short_name], issue_description_line)

        if issue and self._config.rp_bts_project and self._config.rp_bts_url:
            issue_ids = self._get_issue_ids(mark)
            issue_urls = self._get_issue_urls(mark, default_url)
            for issue_id, issue_url in zip(issue_ids, issue_urls):
                issue.external_issue_add(
                    ExternalIssue(
                        bts_url=self._config.rp_bts_url,
                        bts_project=self._config.rp_bts_project,
                        ticket_id=issue_id,
                        url=issue_url,
                    )
                )
        return issue

    def _to_attribute(self, attribute_tuple):
        if attribute_tuple[0]:
            return {"key": attribute_tuple[0], "value": attribute_tuple[1]}
        else:
            return {"value": attribute_tuple[1]}

    def _process_item_name(self, leaf: Dict[str, Any]) -> str:
        """
        Process Item Name if set.

        :param leaf: item context
        :return: Item Name string
        """
        item = leaf["item"]
        name = leaf["name"]
        names = [m for m in item.iter_markers() if m.name == "name"]
        if len(names) > 0:
            mark_name = self._get_item_name(names[0])
            if mark_name:
                name = mark_name
        return name

    def _get_parameters(self, item) -> Optional[Dict[str, Any]]:
        """
        Get params of item.

        :param item: Pytest.Item
        :return: dict of params
        """
        params = item.callspec.params if hasattr(item, "callspec") else None
        if not params:
            return None
        return {str(k): v.replace("\0", "\\0") if isinstance(v, str) else v for k, v in params.items()}

    def _get_parameters_indices(self, item) -> Optional[Dict[str, Any]]:
        """
        Get params indices of item.

        :param item: Pytest.Item
        :return: dict of params indices
        """
        indices = item.callspec.indices if hasattr(item, "callspec") else None
        if not indices:
            return None

        return indices

    def _process_test_case_id(self, leaf: Dict[str, Any]) -> str:
        """
        Process Test Case ID if set.

        :param leaf: item context
        :return: Test Case ID string
        """
        tc_ids = [m for m in leaf["item"].iter_markers() if m.name == "tc_id"]
        if len(tc_ids) > 0:
            return self._get_test_case_id(tc_ids[0], leaf)
        return self._get_test_case_id(None, leaf)

    def _process_issue(self, item: Item) -> Optional[Issue]:
        """
        Process Issue if set.

        :param item: Pytest.Item
        :return: Issue
        """
        issues = [m for m in item.iter_markers() if m.name == "issue"]
        if len(issues) > 0:
            return self._get_issue(issues[0])

    def _process_attributes(self, item: Item) -> List[Dict[str, Any]]:
        """
        Process attributes of item.

        :param item: Pytest.Item
        :return: a set of attributes
        """
        test_attributes = self._config.rp_tests_attributes
        if test_attributes:
            attributes = {
                (attr.get("key", None), attr["value"]) for attr in gen_attributes(self._config.rp_tests_attributes)
            }
        else:
            attributes = set()
        for marker in item.iter_markers():
            if marker.name == "issue":
                if self._config.rp_issue_id_marks:
                    for issue_id in self._get_issue_ids(marker):
                        attributes.add((marker.name, issue_id))
                continue
            if marker.name == "name":
                continue
            if marker.name in self._config.rp_ignore_attributes or marker.name in PYTEST_MARKS_IGNORE:
                continue
            if len(marker.args) > 0:
                attributes.add((marker.name, str(marker.args[0])))
            else:
                attributes.add((None, marker.name))

        return [self._to_attribute(attribute) for attribute in attributes]

    def _process_metadata_item_start(self, leaf: Dict[str, Any]) -> None:
        """
        Process all types of item metadata for its start event.

        :param leaf: item context
        """
        item = leaf["item"]
        leaf["name"] = self._process_item_name(leaf)
        leaf["description"] = self._get_item_description(item)
        leaf["parameters"] = self._get_parameters(item)
        leaf["parameters_indices"] = self._get_parameters_indices(item)
        leaf["code_ref"] = self._get_code_ref(item)
        leaf["test_case_id"] = self._process_test_case_id(leaf)
        leaf["issue"] = self._process_issue(item)
        leaf["attributes"] = self._process_attributes(item)

    def _process_metadata_item_finish(self, leaf: Dict[str, Any]) -> None:
        """
        Process all types of item metadata for its finish event.

        :param leaf: item context
        """
        item = leaf["item"]
        leaf["attributes"] = self._process_attributes(item)
        leaf["issue"] = self._process_issue(item)

    def _build_start_step_rq(self, leaf: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "attributes": leaf.get("attributes", None),
            "name": self._truncate_item_name(leaf["name"]),
            "description": leaf["description"],
            "start_time": timestamp(),
            "item_type": "STEP",
            "code_ref": leaf.get("code_ref", None),
            "parameters": leaf.get("parameters", None),
            "parent_item_id": self._lock(leaf["parent"], lambda p: p["item_id"]),
            "test_case_id": leaf.get("test_case_id", None),
        }
        return payload

    def _start_step(self, step_rq: Dict[str, Any]) -> Optional[str]:
        LOGGER.debug("ReportPortal - Start TestItem: request_body=%s", step_rq)
        return self.rp.start_test_item(**step_rq)

    def __unique_id(self) -> str:
        return str(os.getpid()) + "-" + str(threading.current_thread().ident)

    def __started(self) -> bool:
        return self.__unique_id() in self._start_tracker

    @check_rp_enabled
    def start_pytest_item(self, test_item: Optional[Item] = None):
        """
        Start pytest_item.

        :param test_item: pytest.Item
        :return: None
        """
        if test_item is None:
            return

        if not self.__started():
            self.start()

        if PYTEST_BDD and test_item.location[0].endswith("/pytest_bdd/scenario.py"):
            self._bdd_item_by_name[test_item.name] = test_item
            return

        self._create_suite_path(test_item)
        current_leaf = self._tree_path[test_item][-1]
        self._process_metadata_item_start(current_leaf)
        item_id = self._start_step(self._build_start_step_rq(current_leaf))
        current_leaf["item_id"] = item_id
        current_leaf["exec"] = ExecStatus.IN_PROGRESS

    def process_results(self, test_item: Item, report):
        """
        Save test item results after execution.

        :param test_item: pytest.Item
        :param report:    pytest's result report
        """
        if report.longrepr:
            self.post_log(test_item, report.longreprtext, log_level="ERROR")

        if PYTEST_BDD and test_item.location[0].endswith("/pytest_bdd/scenario.py"):
            return

        leaf = self._tree_path[test_item][-1]
        # Defining test result
        if report.when == "setup":
            leaf["status"] = "PASSED"

        if report.failed:
            leaf["status"] = "FAILED"
            return

        if report.skipped:
            if leaf["status"] in (None, "PASSED"):
                leaf["status"] = "SKIPPED"

    def _build_finish_step_rq(self, leaf: Dict[str, Any]) -> Dict[str, Any]:
        issue = leaf.get("issue", None)
        status = leaf.get("status", "PASSED")
        if status == "SKIPPED" and not self._config.rp_is_skipped_an_issue:
            issue = NOT_ISSUE
        if status == "PASSED":
            issue = None
        payload = {
            "attributes": leaf.get("attributes", None),
            "end_time": timestamp(),
            "status": status,
            "issue": issue,
            "item_id": leaf["item_id"],
        }
        return payload

    def _finish_step(self, finish_rq: Dict[str, Any]) -> None:
        LOGGER.debug("ReportPortal - Finish TestItem: request_body=%s", finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _finish_suite(self, finish_rq: Dict[str, Any]) -> None:
        LOGGER.debug("ReportPortal - End TestSuite: request_body=%s", finish_rq)
        self.rp.finish_test_item(**finish_rq)

    def _build_finish_suite_rq(self, leaf) -> Dict[str, Any]:
        payload = {"end_time": timestamp(), "item_id": leaf["item_id"]}
        return payload

    def _proceed_suite_finish(self, leaf) -> None:
        if leaf.get("exec", ExecStatus.FINISHED) == ExecStatus.FINISHED:
            return

        self._finish_suite(self._build_finish_suite_rq(leaf))
        leaf["exec"] = ExecStatus.FINISHED

    def _finish_parents(self, leaf: Dict[str, Any]) -> None:
        if (
            "parent" not in leaf
            or leaf["parent"] is None
            or leaf["parent"]["type"] is LeafType.ROOT
            or leaf["parent"].get("exec", ExecStatus.FINISHED) == ExecStatus.FINISHED
        ):
            return

        for item, child_leaf in leaf["parent"]["children"].items():
            current_status = child_leaf["exec"]
            if current_status != ExecStatus.FINISHED:
                current_status = self._lock(child_leaf, lambda p: p["exec"])
                if current_status != ExecStatus.FINISHED:
                    return

        self._lock(leaf["parent"], lambda p: self._proceed_suite_finish(p))
        self._finish_parents(leaf["parent"])

    @check_rp_enabled
    def finish_pytest_item(self, test_item: Optional[Item] = None) -> None:
        """Finish pytest_item.

        :param test_item: pytest.Item
        :return: None
        """
        if test_item is None:
            return

        leaf = self._tree_path[test_item][-1]
        self._process_metadata_item_finish(leaf)

        if PYTEST_BDD and test_item.location[0].endswith("/pytest_bdd/scenario.py"):
            del self._bdd_item_by_name[test_item.name]
            return

        self._finish_step(self._build_finish_step_rq(leaf))
        leaf["exec"] = ExecStatus.FINISHED
        self._finish_parents(leaf)

    def _get_items(self, exec_status) -> List[Item]:
        return [k for k, v in self._tree_path.items() if v[-1]["exec"] == exec_status]

    def finish_suites(self) -> None:
        """
        Finish all suites in run with status calculations.

        If an execution passes in multiprocessing mode we don't know which and
        how many items will be passed to our process. Because of that we don't
        finish suites until the very last step. And after that we finish them
        at once.
        """
        # Ensure there is no running items
        finish_time = time()
        while (
            len(self._get_items(ExecStatus.IN_PROGRESS)) > 0 and time() - finish_time <= self._config.rp_launch_timeout
        ):
            sleep(0.1)
        skipped_items = self._get_items(ExecStatus.CREATED)
        for item in skipped_items:
            path = list(self._tree_path[item])
            path.reverse()
            for leaf in path[1:-1]:
                if leaf["exec"] == ExecStatus.IN_PROGRESS:
                    self._lock(leaf, lambda p: self._proceed_suite_finish(p))

    def _build_finish_launch_rq(self) -> Dict[str, Any]:
        finish_rq = {"end_time": timestamp()}
        return finish_rq

    def _finish_launch(self, finish_rq) -> None:
        LOGGER.debug("ReportPortal - Finish launch: request_body=%s", finish_rq)
        self.rp.finish_launch(**finish_rq)

    @check_rp_enabled
    def finish_launch(self) -> None:
        """Finish test launch."""
        # To finish launch session str parameter is needed
        self._finish_launch(self._build_finish_launch_rq())

    def _build_log(
        self, item_id: str, message: str, log_level: str, attachment: Optional[Any] = None
    ) -> Dict[str, Any]:
        sl_rq = {
            "item_id": item_id,
            "time": timestamp(),
            "message": message,
            "level": log_level,
        }
        if attachment:
            sl_rq["attachment"] = attachment
        return sl_rq

    @check_rp_enabled
    def post_log(
        self, test_item: Item, message: str, log_level: str = "INFO", attachment: Optional[Any] = None
    ) -> None:
        """
        Send a log message to the Report Portal.

        :param test_item: pytest.Item
        :param message:    message in log body
        :param log_level:   a level of a log entry (ERROR, WARN, INFO, DEBUG,
        TRACE, FATAL, UNKNOWN)
        :param attachment: attachment file
        :return: None
        """
        if log_level not in KNOWN_LOG_LEVELS:
            LOGGER.warning(
                "Incorrect loglevel = %s. Force set to INFO. " "Available levels: %s.", log_level, KNOWN_LOG_LEVELS
            )
        item_id = self._tree_path[test_item][-1]["item_id"]
        if PYTEST_BDD:
            if not item_id:
                # Check if we are actually a BDD scenario
                scenario = self._bdd_scenario_by_item[test_item]
                if scenario:
                    # Yes, we are a BDD scenario, report log to the scenario
                    item_id = self._tree_path[scenario][-1]["item_id"]

        sl_rq = self._build_log(item_id, message, log_level, attachment)
        self.rp.log(**sl_rq)

    def report_fixture(self, name: str, error_msg: str) -> Generator[None, Any, None]:
        """Report fixture setup and teardown.

        :param name:       Name of the fixture
        :param error_msg:  Error message
        """
        if not self.rp:
            yield
            return

        reporter = self.rp.step_reporter
        item_id = reporter.start_nested_step(name, timestamp())

        try:
            outcome = yield
            exc_info = outcome.excinfo
            exception = exc_info[1] if exc_info else None
            status = "PASSED"
            if exception:
                if type(exception).__name__ != "Skipped":
                    status = "FAILED"
                    error_log = self._build_log(item_id, error_msg, log_level="ERROR")
                    self.rp.log(**error_log)
                    traceback_str = "\n".join(
                        traceback.format_exception(outcome.excinfo[0], value=exception, tb=exc_info[2])
                    )
                    exception_log = self._build_log(item_id, traceback_str, log_level="ERROR")
                    self.rp.log(**exception_log)
            reporter.finish_nested_step(item_id, timestamp(), status)
        except Exception as e:
            LOGGER.error("Failed to report fixture: %s", name)
            LOGGER.exception(e)
            reporter.finish_nested_step(item_id, timestamp(), "FAILED")

    def _get_python_name(self, scenario: Scenario) -> str:
        python_name = f"test_{make_python_name(self._get_scenario_template(scenario).name)}"
        same_item_names = [name for name in self._bdd_item_by_name.keys() if name.startswith(python_name)]
        if len(same_item_names) < 1:
            return python_name
        else:
            return same_item_names[-1]  # Should work fine, since we use OrderedDict

    def start_bdd_scenario(self, feature: Feature, scenario: Scenario) -> None:
        """Save BDD scenario and Feature to test tree. The scenario will be started later if a step will be reported.

        :param feature:  pytest_bdd.Feature
        :param scenario: pytest_bdd.Scenario
        """
        if not PYTEST_BDD:
            return
        item_name = self._get_python_name(scenario)
        test_item = self._bdd_item_by_name.get(item_name, None)
        self._bdd_scenario_by_item[test_item] = scenario
        self._bdd_item_by_scenario[scenario] = test_item

        root_leaf = self._bdd_tree
        if not root_leaf:
            self._bdd_tree = root_leaf = self._create_leaf(LeafType.ROOT, None, None, item_id=self.parent_item_id)
        # noinspection PyTypeChecker
        children_leafs: Dict[Any, Any] = root_leaf["children"]
        if feature in children_leafs:
            feature_leaf = children_leafs[feature]
        else:
            feature_leaf = self._create_leaf(LeafType.FILE, root_leaf, feature)
            children_leafs[feature] = feature_leaf
        children_leafs = feature_leaf["children"]
        rule = getattr(scenario, "rule", None)
        if rule:
            if rule in children_leafs:
                rule_leaf = children_leafs[rule]
            else:
                rule_leaf = self._create_leaf(LeafType.SUITE, feature_leaf, rule)
                children_leafs[rule] = rule_leaf
        else:
            rule_leaf = feature_leaf
        children_leafs = rule_leaf["children"]
        scenario_leaf = self._create_leaf(LeafType.CODE, rule_leaf, scenario)
        children_leafs[scenario] = scenario_leaf
        children_leafs = scenario_leaf["children"]
        background = feature.background
        if background:
            if background not in children_leafs:
                background_leaf = self._create_leaf(LeafType.NESTED, rule_leaf, background)
                children_leafs[background] = background_leaf

        self._remove_file_names(root_leaf)
        self._generate_names(root_leaf)
        if not self._config.rp_hierarchy_code:
            try:
                self._merge_code_with_separator(root_leaf, " - ")
            except Exception as e:
                LOGGER.exception(e)
        self._build_item_paths(root_leaf, [])

    def finish_bdd_scenario(self, feature: Feature, scenario: Scenario) -> None:
        """Finish BDD scenario. Skip if it was not started.

        :param feature:  pytest_bdd.Feature
        :param scenario: pytest_bdd.Scenario
        """
        if not PYTEST_BDD:
            return

        leaf = self._tree_path[scenario][-1]
        if leaf["exec"] != ExecStatus.IN_PROGRESS:
            return
        self._finish_step(self._build_finish_step_rq(leaf))
        leaf["exec"] = ExecStatus.FINISHED
        self._finish_parents(leaf)

    def _get_scenario_parameters_from_template(self, scenario: Scenario) -> Optional[Dict[str, str]]:
        """Get scenario parameters from its template by comparing steps.

        :param scenario: The scenario instance
        :return: A dictionary with parameter names and values, or None if no parameters found
        """
        item = self._bdd_item_by_scenario.get(scenario, None)
        if not item:
            return None
        item_params = item.callspec.params if hasattr(item, "callspec") else None
        if not item_params:
            return None
        if "_pytest_bdd_example" in item_params:
            return OrderedDict(item_params["_pytest_bdd_example"])
        return None

    def _get_scenario_code_ref(self, scenario: Scenario, scenario_template: Optional[ScenarioTemplate]) -> str:
        code_ref = scenario.feature.rel_filename + "/"
        rule = getattr(scenario, "rule", None)
        if rule:
            code_ref += f"[RULE:{rule.name}]/"
        if scenario_template and scenario_template.templated and scenario_template.examples:
            parameters = self._get_scenario_parameters_from_template(scenario)
            if parameters:
                parameters_str = ";".join([f"{k}:{v}" for k, v in sorted(parameters.items())])
                parameters_str = f"[{parameters_str}]" if parameters_str else ""
            else:
                parameters_str = ""
            code_ref += f"[EXAMPLE:{scenario.name}{parameters_str}]"
        else:
            keyword = getattr(scenario, "keyword", "Scenario").upper()
            code_ref += f"[{keyword}:{scenario.name}]"

        return code_ref

    def _get_scenario_test_case_id(self, leaf: Dict[str, Any]) -> str:
        attributes = leaf.get("attributes", [])
        params: Optional[Dict[str, str]] = leaf.get("parameters", None)
        for attribute in attributes:
            if attribute.get("key", None) == "tc_id":
                tc_id = attribute["value"]
                params_str = ""
                if params:
                    params_str = ";".join([f"{k}:{v}" for k, v in sorted(params.items())])
                    params_str = f"[{params_str}]"
                return f"{tc_id}{params_str}"
        return leaf["code_ref"]

    def _process_scenario_metadata(self, leaf: Dict[str, Any]) -> None:
        """
        Process all types of scenario metadata for its start event.

        :param leaf: item context
        """
        scenario = leaf["item"]
        description = (
            "\n".join(scenario.description) if isinstance(scenario.description, list) else scenario.description
        ).rstrip("\n")
        leaf["description"] = description if description else None
        scenario_template = self._get_scenario_template(scenario)
        if scenario_template and scenario_template.templated:
            parameters = self._get_scenario_parameters_from_template(scenario)
            leaf["parameters"] = parameters
            if parameters:
                parameters_str = f"Parameters:\n\n{markdown_helpers.format_data_table_dict(parameters)}"
                if leaf["description"]:
                    leaf["description"] = markdown_helpers.as_two_parts(leaf["description"], parameters_str)
                else:
                    leaf["description"] = parameters_str
        leaf["code_ref"] = self._get_scenario_code_ref(scenario, scenario_template)
        leaf["attributes"] = self._process_bdd_attributes(scenario)
        leaf["test_case_id"] = self._get_scenario_test_case_id(leaf)

    def _finish_bdd_step(self, leaf: Dict[str, Any], status: str) -> None:
        if leaf["exec"] != ExecStatus.IN_PROGRESS:
            return

        reporter = self.rp.step_reporter
        item_id = leaf["item_id"]
        reporter.finish_nested_step(item_id, timestamp(), status)
        leaf["exec"] = ExecStatus.FINISHED

    def _is_background_step(self, step: Step, feature: Feature) -> bool:
        """Check if step belongs to feature background.

        :param step: Current step
        :param feature: Current feature
        :return: True if step is from background, False otherwise
        """
        if not feature.background:
            return False

        background_steps = feature.background.steps
        return any(
            s.name == step.name and s.keyword == step.keyword and s.line_number == step.line_number
            for s in background_steps
        )

    @check_rp_enabled
    def start_bdd_step(self, feature: Feature, scenario: Scenario, step: Step) -> None:
        """Start BDD step.

        :param feature:  pytest_bdd.Feature
        :param scenario: pytest_bdd.Scenario
        :param step:     pytest_bdd.Step
        """
        if not PYTEST_BDD:
            return

        self._create_suite_path(scenario)
        scenario_leaf = self._tree_path[scenario][-1]
        if scenario_leaf["exec"] != ExecStatus.IN_PROGRESS:
            self._process_scenario_metadata(scenario_leaf)
            scenario_leaf["item_id"] = self._start_step(self._build_start_step_rq(scenario_leaf))
            scenario_leaf["exec"] = ExecStatus.IN_PROGRESS
        reporter = self.rp.step_reporter
        step_leaf = self._create_leaf(LeafType.NESTED, scenario_leaf, step)
        if self._is_background_step(step, feature):
            background_leaf = scenario_leaf["children"][feature.background]
            background_leaf["children"][step] = step_leaf
            if background_leaf["exec"] != ExecStatus.IN_PROGRESS:
                item_id = reporter.start_nested_step(BACKGROUND_STEP_NAME, timestamp())
                background_leaf["item_id"] = item_id
                background_leaf["exec"] = ExecStatus.IN_PROGRESS
        else:
            scenario_leaf["children"][step] = step_leaf
            if feature.background:
                background_leaf = scenario_leaf["children"][feature.background]
                self._finish_bdd_step(background_leaf, "PASSED")
        item_id = reporter.start_nested_step(self._truncate_item_name(f"{step.keyword} {step.name}"), timestamp())
        step_leaf["item_id"] = item_id
        step_leaf["exec"] = ExecStatus.IN_PROGRESS

    @check_rp_enabled
    def finish_bdd_step(self, feature: Feature, scenario: Scenario, step: Step) -> None:
        """Finish BDD step.

        :param feature:  pytest_bdd.Feature
        :param scenario: pytest_bdd.Scenario
        :param step:     pytest_bdd.Step
        """
        if not PYTEST_BDD:
            return

        scenario_leaf = self._tree_path[scenario][-1]
        background_steps = []
        if feature.background:
            background_steps = feature.background.steps
        if next(
            filter(
                lambda s: s.name == step.name and s.keyword == step.keyword and s.line_number == step.line_number,
                background_steps,
            ),
            None,
        ):
            parent_leaf = scenario_leaf["children"][feature.background]
        else:
            parent_leaf = scenario_leaf
        step_leaf = parent_leaf["children"][step]
        self._finish_bdd_step(step_leaf, "PASSED")

    @check_rp_enabled
    def finish_bdd_step_error(self, feature: Feature, scenario: Scenario, step: Step, exception: Exception) -> None:
        """Report BDD step error.

        :param feature:   pytest_bdd.Feature
        :param scenario:  pytest_bdd.Scenario
        :param step:      pytest_bdd.Step
        :param exception: Exception
        """
        if not PYTEST_BDD:
            return

        scenario_leaf = self._tree_path[scenario][-1]
        scenario_leaf["status"] = "FAILED"
        if step.background:
            step_leaf = scenario_leaf["children"][step.background]["children"][step]
        else:
            step_leaf = scenario_leaf["children"][step]
        item_id = step_leaf["item_id"]
        traceback_str = "\n".join(
            traceback.format_exception(type(exception), value=exception, tb=exception.__traceback__)
        )
        exception_log = self._build_log(item_id, traceback_str, log_level="ERROR")
        client = self.rp.step_reporter.client
        client.log(**exception_log)

        self._finish_bdd_step(step_leaf, "FAILED")
        if step.background:
            background_leaf = scenario_leaf["children"][step.background]
            self._finish_bdd_step(background_leaf, "FAILED")

    def start(self) -> None:
        """Start servicing Report Portal requests."""
        self.parent_item_id = self._config.rp_parent_item_id
        self.ignored_attributes = list(set(self._config.rp_ignore_attributes or []).union({"parametrize"}))
        LOGGER.debug(
            "ReportPortal - Init service: endpoint=%s, " "project=%s, api_key=%s",
            self._config.rp_endpoint,
            self._config.rp_project,
            self._config.rp_api_key,
        )
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
            log_batch_payload_limit=self._config.rp_log_batch_payload_limit,
            launch_uuid_print=self._config.rp_launch_uuid_print,
            print_output=self._config.rp_launch_uuid_print_output,
            http_timeout=self._config.rp_http_timeout,
            mode=self._config.rp_mode,
            # OAuth 2.0 parameters
            oauth_uri=self._config.rp_oauth_uri,
            oauth_username=self._config.rp_oauth_username,
            oauth_password=self._config.rp_oauth_password,
            oauth_client_id=self._config.rp_oauth_client_id,
            oauth_client_secret=self._config.rp_oauth_client_secret,
            oauth_scope=self._config.rp_oauth_scope,
        )
        if hasattr(self.rp, "get_project_settings"):
            self.project_settings = self.rp.get_project_settings()
        # noinspection PyUnresolvedReferences
        self._start_tracker.add(self.__unique_id())

    def stop(self) -> None:
        """Finish servicing Report Portal requests."""
        self.rp.close()
        self.rp = None
        self._start_tracker.remove(self.__unique_id())
