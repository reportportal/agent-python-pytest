import logging
from time import time
from reportportal_client import (
    ReportPortalService, FinishExecutionRQ, StartLaunchRQ, StartTestItemRQ,
    FinishTestItemRQ, SaveLogRQ)


def timestamp():
    return str(int(time() * 1000))


class PyTestService(object):

    RP = None
    TEST_ITEM_STACK = []
    launch_id = None

    @staticmethod
    def init_service(endpoint, project, uuid):

        if PyTestService.RP is None:
            logging.debug(
                msg="ReportPortal - Init service: "
                    "endpoint={0}, project={1}, uuid={2}".
                    format(endpoint, project, uuid))
            PyTestService.RP = ReportPortalService(
                endpoint=endpoint,
                project=project,
                token=uuid)
        else:
            raise Exception("PyTest is initialized")
        return PyTestService.RP

    @staticmethod
    def start_launch(launch_name=None, mode=None):
        # TODO: Tags, values could be moved to separated module like helper
        tags = ["PyTest"]
        sl_pt = StartLaunchRQ(
            name=launch_name,
            start_time=timestamp(),
            description="PyTest_Launch",
            mode=mode,
            tags=tags)
        logging.debug(msg="ReportPortal - Start launch: "
                          "request_body={0}".format(sl_pt.data))
        req_data = PyTestService.RP.start_launch(sl_pt)
        logging.debug(msg="ReportPortal - Launch started: "
                          "response_body={0}".format(req_data.raw))
        PyTestService.launch_id = req_data.id

        PyTestService.TEST_ITEM_STACK.append((None, "SUITE"))
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(PyTestService.TEST_ITEM_STACK))

    @staticmethod
    def start_pytest_item(test_item=None):
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
            launch_id=PyTestService.launch_id,
            type="TEST")

        parent_item_id = PyTestService._get_top_id_from_stack()

        logging.debug(
            msg="ReportPortal - Start TestItem: "
            "request_body={0}, parent_item={1}".format(
                start_rq.data, parent_item_id))

        req_data = PyTestService.RP.start_test_item(
            parent_item_id=parent_item_id, start_test_item_rq=start_rq)

        PyTestService.TEST_ITEM_STACK.append((req_data.id, "TEST"))
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(PyTestService.TEST_ITEM_STACK))

    @staticmethod
    def finish_pytest_item(status, issue=None):
        fta_rq = FinishTestItemRQ(end_time=timestamp(),
                                  status=status,
                                  issue=issue)

        test_item_id = PyTestService._get_top_id_from_stack()
        logging.debug(
            msg="ReportPortal - Finish TetsItem:"
                " request_body={0}, test_id={1}".
                format(fta_rq.data, test_item_id))
        PyTestService.RP.finish_test_item(
            item_id=test_item_id,
            finish_test_item_rq=fta_rq)
        PyTestService.TEST_ITEM_STACK.pop()
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(PyTestService.TEST_ITEM_STACK))

    @staticmethod
    def finish_launch(status):
        fl_rq = FinishExecutionRQ(
            end_time=timestamp(),
            status=status)
        launch_id = PyTestService.launch_id
        logging.debug(msg="ReportPortal - Finish launch: "
                          "request_body={0}, launch_id={1}".format(fl_rq.data,
                                                                   launch_id))
        PyTestService.RP.finish_launch(launch_id, fl_rq)
        PyTestService.TEST_ITEM_STACK.pop()
        logging.debug(
            msg="ReportPortal - Stack: {0}".
                format(PyTestService.TEST_ITEM_STACK))

    @staticmethod
    def _get_top_id_from_stack():
        try:
            return PyTestService.TEST_ITEM_STACK[-1][0]
        except IndexError:
            return None

    @staticmethod
    def post_log(message, log_level="DEBUG"):
        sl_rq = SaveLogRQ(item_id=PyTestService._get_top_id_from_stack(),
                          time=timestamp(), message=message,
                          level=log_level)
        PyTestService.RP.log(sl_rq)
