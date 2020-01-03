import logging
import sys
import traceback
from time import time

import pkg_resources
import pytest
from _pytest.doctest import DoctestItem
from _pytest.main import Session

try:
    pkg_resources.get_distribution('pytest >= 3.4.0')
    from _pytest.nodes import File, Item
except pkg_resources.VersionConflict:
    from _pytest.main import File, Item

try:
    pkg_resources.get_distribution('pytest >= 3.8.0')
    from _pytest.warning_types import PytestWarning
except pkg_resources.VersionConflict:
    from pytest_reportportal.errors import PytestWarning


from _pytest.python import Class, Function, Instance, Module
from _pytest.unittest import TestCaseFunction, UnitTestCase

from reportportal_client import ReportPortalServiceAsync
from six import with_metaclass
from six.moves import queue

log = logging.getLogger(__name__)


def timestamp():
    return str(int(time() * 1000))


def trim_docstring(docstring):
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


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


class PyTestServiceClass(with_metaclass(Singleton, object)):

    def __init__(self):
        self.RP = None
        try:
            pkg_resources.get_distribution('reportportal_client >= 3.2.0')
            self.RP_SUPPORTS_PARAMETERS = True
        except pkg_resources.VersionConflict:
            self.RP_SUPPORTS_PARAMETERS = False

        self.ignore_errors = True
        self.ignored_tags = []

        self._errors = queue.Queue()
        self._loglevels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')
        self._hier_parts = {}
        self._item_parts = {}

    def init_service(self, endpoint, project, uuid, log_batch_size,
                     ignore_errors, ignored_tags, verify_ssl=True,
                     retries=0):
        self._errors = queue.Queue()
        if self.RP is None:
            self.ignore_errors = ignore_errors
            if self.RP_SUPPORTS_PARAMETERS:
                self.ignored_tags = list(set(ignored_tags).union({'parametrize'}))
            else:
                self.ignored_tags = ignored_tags
            log.debug('ReportPortal - Init service: endpoint=%s, '
                      'project=%s, uuid=%s', endpoint, project, uuid)
            self.RP = ReportPortalServiceAsync(
                endpoint=endpoint,
                project=project,
                token=uuid,
                error_handler=self.async_error_handler,
                retries=retries,
                log_batch_size=log_batch_size,
                verify_ssl=verify_ssl
            )
            if self.RP and hasattr(self.RP.rp_client, "get_project_settings"):
                self.project_settings = self.RP.rp_client.get_project_settings()
            else:
                self.project_settings = None
            self.issue_types = self.get_issue_types()
        else:
            log.debug('The pytest is already initialized')
        return self.RP

    def async_error_handler(self, exc_info):
        self.terminate_service(nowait=True)
        self.RP = None
        self._errors.put_nowait(exc_info)

    def terminate_service(self, nowait=False):
        if self.RP is not None:
            self.RP.terminate(nowait)
            self.RP = None

    def start_launch(self, launch_name,
                     mode=None,
                     tags=None,
                     description=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        sl_pt = {
            'name': launch_name,
            'start_time': timestamp(),
            'description': description,
            'mode': mode,
            'tags': tags
        }
        log.debug('ReportPortal - Start launch: equest_body=%s', sl_pt)
        req_data = self.RP.start_launch(**sl_pt)
        log.debug('ReportPortal - Launch started: response_body=%s', req_data)

    def collect_tests(self, session):
        self._stop_if_necessary()
        if self.RP is None:
            return

        hier_dirs = False
        hier_module = False
        hier_class = False
        hier_param = False
        display_suite_file_name = True

        if not hasattr(session.config, 'slaveinput'):
            hier_dirs = session.config.getini('rp_hierarchy_dirs')
            hier_module = session.config.getini('rp_hierarchy_module')
            hier_class = session.config.getini('rp_hierarchy_class')
            hier_param = session.config.getini('rp_hierarchy_parametrize')
            display_suite_file_name = session.config.getini('rp_display_suite_test_file')

        try:
            hier_dirs_level = int(session.config.getini('rp_hierarchy_dirs_level'))
        except ValueError:
            hier_dirs_level = 0

        dirs_parts = {}
        tests_parts = {}

        for item in session.items:
            # Start collecting test item parts
            parts = []

            # Hierarchy for directories
            rp_name = self._add_item_hier_parts_dirs(item, hier_dirs, hier_dirs_level, parts, dirs_parts)

            # Hierarchy for Module and Class/UnitTestCase
            item_parts = self._get_item_parts(item)
            rp_name = self._add_item_hier_parts_other(item_parts, item, Module, hier_module, parts, rp_name)
            rp_name = self._add_item_hier_parts_other(item_parts, item, Class, hier_class, parts, rp_name)
            rp_name = self._add_item_hier_parts_other(item_parts, item, UnitTestCase, hier_class, parts, rp_name)

            # Hierarchy for parametrized tests
            if hier_param:
                rp_name = self._add_item_hier_parts_parametrize(item, parts, tests_parts, rp_name)

            # Hierarchy for test itself (Function/TestCaseFunction)
            item._rp_name = rp_name + ("::" if rp_name else "") + item.name

            # Result initialization
            for part in parts:
                part._rp_result = "PASSED"

            self._item_parts[item] = parts
            for part in parts:
                if '_pytest.python.Class' in str(type(part)) and not display_suite_file_name and not hier_module:
                    part._rp_name = part._rp_name.split("::")[-1]
                if part not in self._hier_parts:
                    self._hier_parts[part] = {"finish_counter": 1, "start_flag": False}
                else:
                    self._hier_parts[part]["finish_counter"] += 1

    def start_pytest_item(self, test_item=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        for part in self._item_parts[test_item]:
            if self._hier_parts[part]["start_flag"]:
                continue
            self._hier_parts[part]["start_flag"] = True

            payload = {
                'name': self._get_item_name(part),
                'description': self._get_item_description(part),
                'tags': self._get_item_tags(part),
                'start_time': timestamp(),
                'item_type': 'SUITE'
            }
            log.debug('ReportPortal - Start Suite: request_body=%s', payload)
            self.RP.start_test_item(**payload)

        start_rq = {
            'name': self._get_item_name(test_item),
            'description': self._get_item_description(test_item),
            'tags': self._get_item_tags(test_item),
            'start_time': timestamp(),
            'item_type': 'STEP'
        }
        if self.RP_SUPPORTS_PARAMETERS:
            start_rq['parameters'] = self._get_parameters(test_item)

        log.debug('ReportPortal - Start TestItem: request_body=%s', start_rq)
        self.RP.start_test_item(**start_rq)

    def is_item_update_supported(self):
        """Check item update API call client support."""
        return hasattr(self.RP, "update_test_item")

    def update_pytest_item(self, test_item=None):
        """Make item update API call.

        :param test_item: pytest test item
        """
        self._stop_if_necessary()
        if self.RP is None:
            return

        # if update_test_item is not supported in client
        if not self.is_item_update_supported():
            log.debug('ReportPortal - Update TestItem: method is not defined')
            return

        start_rq = {
            'description': self._get_item_description(test_item),
            'tags': self._get_item_tags(test_item),
        }
        log.debug('ReportPortal - Update TestItem: request_body=%s', start_rq)
        self.RP.update_test_item(**start_rq)

    def finish_pytest_item(self, test_item, status, issue=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        fta_rq = {
            'end_time': timestamp(),
            'status': status,
            'issue': issue
        }

        log.debug('ReportPortal - Finish TestItem: request_body=%s', fta_rq)
        self.RP.finish_test_item(**fta_rq)

        parts = self._item_parts[test_item]
        while len(parts) > 0:
            part = parts.pop()
            if status == "FAILED":
                part._rp_result = status
            self._hier_parts[part]["finish_counter"] -= 1
            if self._hier_parts[part]["finish_counter"] > 0:
                continue
            payload = {
                'end_time': timestamp(),
                'issue': issue,
                'status': part._rp_result
            }
            log.debug('ReportPortal - End TestSuite: request_body=%s', payload)
            self.RP.finish_test_item(**payload)

    def finish_launch(self, status='rp_launch', force=False):
        self._stop_if_necessary()
        if self.RP is None:
            return

        # To finish launch session str parameter is needed
        fl_rq = {
            'end_time': timestamp(),
            'status': status
        }
        log.debug('ReportPortal - Finish launch: request_body=%s', fl_rq)
        if not force:
            self.RP.finish_launch(**fl_rq)
        else:
            self.RP.stop_launch(**fl_rq)

    def post_log(self, message, loglevel='INFO', attachment=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        if loglevel not in self._loglevels:
            log.warning('Incorrect loglevel = %s. Force set to INFO. '
                        'Available levels: %s.', loglevel, self._loglevels)
            loglevel = 'INFO'

        sl_rq = {
            'time': timestamp(),
            'message': message,
            'level': loglevel,
            'attachment': attachment,
        }
        self.RP.log(**sl_rq)

    def _stop_if_necessary(self):
        try:
            exc, msg, tb = self._errors.get(False)
            traceback.print_exception(exc, msg, tb)
            sys.stderr.flush()
            if not self.ignore_errors:
                pytest.exit(msg)
        except queue.Empty:
            pass

    def get_issue_types(self):
        issue_types = {}
        if not self.project_settings:
            return issue_types

        for item_type in ("AUTOMATION_BUG", "PRODUCT_BUG", "SYSTEM_ISSUE", "NO_DEFECT", "TO_INVESTIGATE"):
            for item in self.project_settings["subTypes"][item_type]:
                issue_types[item["shortName"]] = item["locator"]

        return issue_types

    @staticmethod
    def _add_item_hier_parts_dirs(item, hier_flag, dirs_level, report_parts, dirs_parts, rp_name=""):

        parts_dirs = PyTestServiceClass._get_item_dirs(item)
        dir_path = item.fspath.new(dirname="", basename="", drive="")
        rp_name_path = ""

        for dir_name in parts_dirs[dirs_level:]:
            dir_path = dir_path.join(dir_name)
            path = str(dir_path)

            if hier_flag:
                if path in dirs_parts:
                    item_dir = dirs_parts[path]
                    rp_name = ""
                else:
                    item_dir = File(dir_name, nodeid=dir_name, session=item.session, config=item.session.config)
                    rp_name += dir_name
                    item_dir._rp_name = rp_name
                    dirs_parts[path] = item_dir
                    rp_name = ""

                report_parts.append(item_dir)
            else:
                rp_name_path = path[1:]

        if not hier_flag:
            rp_name += rp_name_path

        return rp_name

    @staticmethod
    def _add_item_hier_parts_parametrize(item, report_parts, tests_parts, rp_name=""):

        for mark in item.own_markers:
            if mark.name == 'parametrize':
                ch_index = item.nodeid.find("[")
                test_fullname = item.nodeid[:ch_index if ch_index > 0 else len(item.nodeid)]
                test_name = item.originalname

                rp_name += ("::" if rp_name else "") + test_name

                if test_fullname in tests_parts:
                    item_test = tests_parts[test_fullname]
                else:
                    item_test = Item(test_fullname, nodeid=test_fullname, session=item.session,
                                     config=item.session.config)
                    item_test._rp_name = rp_name
                    item_test.obj = item.obj
                    item_test.keywords = item.keywords
                    item_test.own_markers = item.own_markers
                    item_test.parent = item.parent

                    tests_parts[test_fullname] = item_test

                rp_name = ""
                report_parts.append(item_test)
                break

        return rp_name

    @staticmethod
    def _add_item_hier_parts_other(item_parts, item, item_type, hier_flag, report_parts, rp_name=""):

        for part in item_parts:

            if type(part) is item_type:

                if item_type is Module:
                    module_path = str(item.fspath.new(dirname=rp_name, basename=part.fspath.basename, drive=""))
                    rp_name = module_path if rp_name else module_path[1:]
                elif item_type in (Class, Function, UnitTestCase, TestCaseFunction):
                    rp_name += ("::" if rp_name else "") + part.name

                if hier_flag:
                    part._rp_name = rp_name
                    rp_name = ""
                    report_parts.append(part)

        return rp_name

    @staticmethod
    def _get_item_parts(item):
        parts = []
        parent = item.parent
        if not isinstance(parent, Instance):
            parts.append(parent)
        while True:
            parent = parent.parent
            if parent is None:
                break
            if isinstance(parent, Instance):
                continue
            if isinstance(parent, Session):
                break
            parts.append(parent)

        parts.reverse()
        return parts

    @staticmethod
    def _get_item_dirs(item):

        root_path = item.session.config.rootdir.strpath
        dir_path = item.fspath.new(basename="")
        rel_dir = dir_path.new(dirname=dir_path.relto(root_path), basename="", drive="")

        dir_list = []
        for directory in rel_dir.parts(reverse=False):
            dir_name = directory.basename
            if dir_name:
                dir_list.append(dir_name)

        return dir_list

    def _get_item_tags(self, item):
        # Try to extract names of @pytest.mark.* decorators used for test item
        # and exclude those which present in rp_ignore_tags parameter
        def get_marker_value(item, keyword):
            try:
                marker = item.get_closest_marker(keyword)
            except AttributeError:
                # pytest < 3.6
                marker = item.keywords.get(keyword)

            return "{}:{}".format(keyword, marker.args[0]) \
                if marker and marker.args else keyword

        try:
            tags = [get_marker_value(item, k) for k in item.keywords
                    if item.get_closest_marker(k) is not None
                    and k not in self.ignored_tags]
        except AttributeError:
            # pytest < 3.6
            tags = [get_marker_value(item, k) for k in item.keywords
                    if item.get_marker(k) is not None
                    and k not in self.ignored_tags]

        tags.extend(item.session.config.getini('rp_tests_tags'))

        return tags

    def _get_parameters(self, item):
        return item.callspec.params if hasattr(item, 'callspec') else {}

    @staticmethod
    def _get_item_name(test_item):
        name = test_item._rp_name
        if len(name) > 256:
            name = name[:256]
            test_item.warn(
                PytestWarning(
                    'Test node ID was truncated to "{}" because of name size '
                    'constrains on reportportal'.format(name)
                )
            )
        return name

    @staticmethod
    def _get_item_description(test_item):
        if isinstance(test_item, (Class, Function, Module, Item)):
            doc = test_item.obj.__doc__
            if doc is not None:
                return trim_docstring(doc)
        if isinstance(test_item, DoctestItem):
            return test_item.reportinfo()[2]
