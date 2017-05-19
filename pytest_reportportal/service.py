import logging
from time import time
from six import with_metaclass
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

    _loglevels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')

    def __init__(self):
        self.RP = None

    def init_service(self, endpoint, project, uuid):
        if self.RP is None:
            logging.debug(
                msg="ReportPortal - Init service: "
                    "endpoint={0}, project={1}, uuid={2}".
                    format(endpoint, project, uuid))
            self.RP = ReportPortalServiceAsync(
                endpoint=endpoint,
                project=project,
                token=uuid)
        else:
            logging.debug("The pytest is already initialized")
        return self.RP

    def terminate_service(self):
        if self.RP is not None:
            self.RP.terminate()

    def start_launch(
            self, launch_name=None, mode=None, tags=None, launch=None):
        # In next versions launch object(suite, testcase)
        # could be set as parameter
        sl_pt = dict(
            name=launch_name,
            start_time=timestamp(),
            description='Pytest Launch',
            mode=mode,
            tags=tags)
        logging.debug("ReportPortal - Start launch: "
                      "request_body={0}".format(sl_pt))
        req_data = self.RP.start_launch(**sl_pt)
        logging.debug("ReportPortal - Launch started: "
                      "response_body={0}".format(req_data))

    def start_pytest_item(self, test_item=None):
        try:
            # for common items
            item_description = test_item.function.__doc__
        except AttributeError:
            # doctest  has no `function` attribute
            item_description = test_item.reportinfo()[2]
        start_rq = dict(
            name=test_item.name,
            description=item_description,
            tags=['PyTest Item Tag'],
            start_time=timestamp(),
            type="TEST")

        logging.debug(
            "ReportPortal - Start TestItem: "
            "request_body={0}".format(start_rq))

        self.RP.start_test_item(**start_rq)

    def finish_pytest_item(self, status, issue=None):
        fta_rq = dict(end_time=timestamp(),
                      status=status,
                      issue=issue)

        logging.debug(
            "ReportPortal - Finish TestItem:"
            " request_body={0}".format(fta_rq))
        self.RP.finish_test_item(**fta_rq)

    def finish_launch(self, launch=None, status="rp_launch"):
        # TO finish launch session str parameter is needed
        fl_rq = dict(
            end_time=timestamp(),
            status=status)
        logging.debug(msg="ReportPortal - Finish launch: "
                          "request_body={0}".format(fl_rq))
        self.RP.finish_launch(**fl_rq)

    def post_log(self, message, loglevel='INFO'):
        if loglevel not in self._loglevels:
            logging.warning('Incorrect loglevel = {}. Force set to INFO. Avaliable levels: '
                            '{}.'.format(loglevel, self._loglevels))
            loglevel = 'INFO'

        sl_rq = dict(time=timestamp(), message=message, level=loglevel)
        self.RP.log(**sl_rq)


PyTestService = PyTestServiceClass()
