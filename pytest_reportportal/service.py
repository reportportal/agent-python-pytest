import logging
from time import time
from six import with_metaclass
from reportportal_client import (
    ReportPortalService, FinishExecutionRQ, StartLaunchRQ, StartTestItemRQ,
    FinishTestItemRQ, SaveLogRQ)


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
        self.TEST_ITEM_STACK = []
        self.launch_id = None
        self.loglevel_map = {
            0: "TRACE",
            10: "DEBUG",
            20: "INFO",
            30: "WARNING",
            40: "ERROR"}

    def init_service(self, endpoint, project, uuid):

        if self.RP is None:
            logging.debug(
                msg="ReportPortal - Init service: "
                    "endpoint={0}, project={1}, uuid={2}".
                    format(endpoint, project, uuid))
            self.RP = ReportPortalService(
                endpoint=endpoint,
                project=project,
                token=uuid)
        else:
            logging.debug("The pytest is already initialized")
        return self.RP

    def start_launch(
            self, launch_name=None, mode=None, tags=None, launch=None):
        # In next versions launch object(suite, testcase)
        # could be set as parameter
        sl_pt = StartLaunchRQ(
            name=launch_name,
            start_time=timestamp(),
            description='Pytest Launch',
            mode=mode,
            tags=tags)
        logging.debug(msg="ReportPortal - Start launch: "
                          "request_body={0}".format(sl_pt.data))
        req_data = self.RP.start_launch(sl_pt)
        logging.debug(msg="ReportPortal - Launch started: "
                          "response_body={0}".format(req_data.raw))
        self.launch_id = req_data.id

        self.TEST_ITEM_STACK.append((None, "SUITE"))
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(self.TEST_ITEM_STACK))

    def start_pytest_item(self, test_item=None):
        try:
            # for common items
            item_description = test_item.function.__doc__
        except AttributeError:
            # doctest  has no `function` attribute
            item_description = test_item.reportinfo()[2]
        start_rq = StartTestItemRQ(
            name=test_item.name,
            description=item_description,
            tags=['PyTest Item Tag'],
            start_time=timestamp(),
            launch_id=self.launch_id,
            type="TEST")

        parent_item_id = self._get_top_id_from_stack()

        logging.debug(
            msg="ReportPortal - Start TestItem: "
            "request_body={0}, parent_item={1}".format(
                start_rq.data, parent_item_id))

        req_data = self.RP.start_test_item(
            parent_item_id=parent_item_id, start_test_item_rq=start_rq)

        self.TEST_ITEM_STACK.append((req_data.id, "TEST"))
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(self.TEST_ITEM_STACK))

    def finish_pytest_item(self, status, issue=None):
        fta_rq = FinishTestItemRQ(end_time=timestamp(),
                                  status=status,
                                  issue=issue)

        test_item_id = self._get_top_id_from_stack()
        logging.debug(
            msg="ReportPortal - Finish TetsItem:"
                " request_body={0}, test_id={1}".
                format(fta_rq.data, test_item_id))
        self.RP.finish_test_item(
            item_id=test_item_id,
            finish_test_item_rq=fta_rq)
        self.TEST_ITEM_STACK.pop()
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(self.TEST_ITEM_STACK))

    def finish_launch(self, launch=None, status="rp_launch"):
        # TO finish launch session str parameter is needed
        fl_rq = FinishExecutionRQ(
            end_time=timestamp(),
            status=status)
        launch_id = self.launch_id
        logging.debug(msg="ReportPortal - Finish launch: "
                          "request_body={0}, launch_id={1}".format(fl_rq.data,
                                                                   launch_id))
        self.RP.finish_launch(launch_id, fl_rq)
        self.TEST_ITEM_STACK.pop()
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(self.TEST_ITEM_STACK))

    def _get_top_id_from_stack(self):
        try:
            return self.TEST_ITEM_STACK[-1][0]
        except IndexError:
            return None

    def post_log(self, message, log_level="INFO"):
        sl_rq = SaveLogRQ(item_id=self._get_top_id_from_stack(),
                          time=timestamp(), message=message,
                          level=self.loglevel_map[log_level])
        self.RP.log(sl_rq)


PyTestService = PyTestServiceClass()
