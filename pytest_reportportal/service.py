import logging
import sys
import traceback
import pytest

from time import time
from six import with_metaclass
from six.moves import queue

from reportportal_client import ReportPortalServiceAsync


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
        self.ignore_errors = True
        self.ignored_tags = []

        self._errors = queue.Queue()
        self._loglevels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')

    def init_service(self, endpoint, project, uuid, log_batch_size,
                     ignore_errors, ignored_tags):
        self._errors = queue.Queue()
        if self.RP is None:
            self.ignore_errors = ignore_errors
            self.ignored_tags = ignored_tags
            logging.debug(
                msg='ReportPortal - Init service: '
                    'endpoint={0}, project={1}, uuid={2}'.
                    format(endpoint, project, uuid))
            self.RP = ReportPortalServiceAsync(
                endpoint=endpoint,
                project=project,
                token=uuid,
                error_handler=self.async_error_handler,
                log_batch_size=log_batch_size
            )
        else:
            logging.debug('The pytest is already initialized')
        return self.RP

    def async_error_handler(self, exc_info):
        self.terminate_service()
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

    def terminate_service(self):
        if self.RP is not None:
            self.RP.terminate()

    def start_launch(
            self, launch_name, mode=None, tags=None, description=None):
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
        logging.debug('ReportPortal - Start launch: '
                      'request_body=%s', sl_pt)
        req_data = self.RP.start_launch(**sl_pt)
        logging.debug('ReportPortal - Launch started: '
                      'response_body=%s', req_data)

    def start_pytest_item(self, test_item=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        start_rq = {
            'name': self._get_full_name(test_item),
            'description': self._get_description(test_item),
            'tags': self._get_tags(test_item),
            'start_time': timestamp(),
            'item_type': 'STEP'
        }

        logging.debug('ReportPortal - Start TestItem: '
                      'request_body=%s', start_rq)
        self.RP.start_test_item(**start_rq)

    def _get_tags(self, test_item):
        # try to extract names of @pytest.mark.* decorators used for test item
        # and exclude those which present in rp_ignore_tags parameter
        mark_plugin = test_item.config.pluginmanager.getplugin('mark')
        if mark_plugin:
            keywords = test_item.keywords
            marks = mark_plugin.MarkMapping(keywords)._mymarks
            return [m for m in marks if m not in self.ignored_tags]
        else:
            return []

    def finish_pytest_item(self, status, issue=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        fta_rq = {
            'end_time': timestamp(),
            'status': status,
            'issue': issue
        }

        logging.debug('ReportPortal - Finish TestItem: '
                      'request_body=%s', fta_rq)
        self.RP.finish_test_item(**fta_rq)

    def finish_launch(self, launch=None, status='rp_launch'):
        self._stop_if_necessary()
        if self.RP is None:
            return

        # To finish launch session str parameter is needed
        fl_rq = {
            'end_time': timestamp(),
            'status': status
        }
        logging.debug('ReportPortal - Finish launch: request_body=%s', fl_rq)
        self.RP.finish_launch(**fl_rq)

    def post_log(self, message, loglevel='INFO', attachment=None):
        self._stop_if_necessary()
        if self.RP is None:
            return

        if loglevel not in self._loglevels:
            logging.warning('Incorrect loglevel = %s. Force set to INFO. '
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
    def _get_full_name(test_item):
        return test_item.nodeid

    @staticmethod
    def _get_description(test_item):
        try:
            # for common items
            return test_item.function.__doc__
        except AttributeError:
            # doctest has no `function` attribute
            return test_item.reportinfo()[2]


PyTestService = PyTestServiceClass()
