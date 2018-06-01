import logging
import sys
import traceback
import pytest
import pkg_resources

from time import time
from six import with_metaclass
from six.moves import queue

from _pytest.main import Session
from _pytest.python import Class, Function, Instance, Module
from _pytest.doctest import DoctestItem
from reportportal_client import ReportPortalServiceAsync

log = logging.getLogger(__name__)


def timestamp():
    return str(int(time() * 1000))


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
        self._start_stack = []
        self._finish_stack = []

    def init_service(self, endpoint, project, uuid, log_batch_size,
                     ignore_errors, ignored_tags):
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
                log_batch_size=log_batch_size
            )
        else:
            log.debug('The pytest is already initialized')
        return self.RP

    def async_error_handler(self, exc_info):
        self.terminate_service(nowait=True)
        self.RP = None
        self._errors.put_nowait(exc_info)

    def _stop_if_necessary(self):
        try:
            exc, msg, tb = self._errors.get(False)
            traceback.print_exception(exc, msg, tb)
            sys.stderr.flush()
            if not self.ignore_errors:
                pytest.exit(msg)
        except queue.Empty:
            pass

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

        for item in session.items:
            # Start collecting test item parts
            parts_in = []
            parts_out = []
            parts = self._get_item_parts(item)
            # Add all parts in revers order to parts_out
            parts_out.extend(reversed(parts))
            while parts:
                part = parts.pop(0)
                if part in self._start_stack:
                    # If we've seen this part, skip it
                    continue
                # We haven't seen this part yet. Could be a Class, Module or Function
                # Appent to parts_in
                parts_in.append(part)

            # Update self._start_stack and self._finish_stack
            self._start_stack.extend(parts_in)
            self._finish_stack.extend(parts_out)

    def start_pytest_item(self, test_item=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        while True:
            part = self._start_stack.pop(0)
            if part is test_item:
                break
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

    def _get_item_parts(self, item):
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
        parts.append(item)
        return parts

    def _get_item_tags(self, item):
        # Try to extract names of @pytest.mark.* decorators used for test item
        # and exclude those which present in rp_ignore_tags parameter
        return [k for k in item.keywords if item.get_marker(k) is not None
                and k not in self.ignored_tags]

    def _get_parameters(self, item):
        return item.callspec.params if hasattr(item, 'callspec') else {}

    def finish_pytest_item(self, status, issue=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        # Remove the test from the finish stack
        self._finish_stack.pop(0)

        fta_rq = {
            'end_time': timestamp(),
            'status': status,
            'issue': issue
        }

        log.debug('ReportPortal - Finish TestItem: request_body=%s', fta_rq)
        self.RP.finish_test_item(**fta_rq)

        while self._finish_stack:
            if isinstance(self._finish_stack[0], Function):
                break
            part = self._finish_stack.pop(0)
            if self._finish_stack.count(part):
                continue
            payload = {
                'end_time': timestamp(),
                'issue': issue,
                'status': 'PASSED'
            }
            log.debug('ReportPortal - End TestSuite: request_body=%s', payload)
            self.RP.finish_test_item(**payload)


    def finish_launch(self, launch=None, status='rp_launch'):
        self._stop_if_necessary()
        if self.RP is None:
            return

        # To finish launch session str parameter is needed
        fl_rq = {
            'end_time': timestamp(),
            'status': status
        }
        log.debug('ReportPortal - Finish launch: request_body=%s', fl_rq)
        self.RP.finish_launch(**fl_rq)

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

    @staticmethod
    def _get_item_name(test_item):
        name = test_item.name
        if len(name) > 256:
            name = name[:256]
            test_item.warn(
                'C1',
                'Test node ID was truncated to "{}" because of name size '
                'constrains on reportportal'.format(name)
            )
        return name

    @staticmethod
    def _get_item_description(test_item):
        if isinstance(test_item, (Class, Function, Module)):
            doc = test_item.obj.__doc__
            if doc is not None:
                return doc.strip()
        if isinstance(test_item, DoctestItem):
            return test_item.reportinfo()[2]
