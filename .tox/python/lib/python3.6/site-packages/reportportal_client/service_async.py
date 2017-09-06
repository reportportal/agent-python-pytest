import sys
import threading
from logging import getLogger

from six.moves import queue

from .service import ReportPortalService
from .errors import Error

logger = getLogger(__name__)


class QueueListener(object):
    _sentinel_item = None

    def __init__(self, queue, *handlers):
        self.queue = queue
        self.handlers = handlers
        self._stop_nowait = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def dequeue(self, block=True):
        """Dequeue a record and return item."""
        return self.queue.get(block)

    def start(self):
        """Start the listener.

        This starts up a background thread to monitor the queue for
        items to process.
        """
        self._thread = t = threading.Thread(target=self._monitor)
        t.setDaemon(True)
        t.start()

    def prepare(self, record):
        """Prepare a record for handling.

        This method just returns the passed-in record. You may want to
        override this method if you need to do any custom marshalling or
        manipulation of the record before passing it to the handlers.
        """
        return record

    def handle(self, record):
        """Handle an item.

        This just loops through the handlers offering them the record
        to handle.
        """
        record = self.prepare(record)
        for handler in self.handlers:
            handler(record)

    def _monitor(self):
        """Monitor the queue for items, and ask the handler to deal with them.

        This method runs on a separate, internal thread.
        The thread will terminate if it sees a sentinel object in the queue.
        """
        err_msg = ("invalid internal state:"
                   " _stop_nowait can not be set if _stop is not set")
        assert self._stop.isSet() or not self._stop_nowait.isSet(), err_msg

        q = self.queue
        has_task_done = hasattr(q, 'task_done')
        while not self._stop.isSet():
            try:
                record = self.dequeue(True)
                if record is self._sentinel_item:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                pass

        # There might still be records in the queue,
        # handle then unless _stop_nowait is set.
        while not self._stop_nowait.isSet():
            try:
                record = self.dequeue(False)
                if record is self._sentinel_item:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break

    def stop(self, nowait=False):
        """Stop the listener.

        This asks the thread to terminate, and then waits for it to do so.
        Note that if you don't call this before your application exits, there
        may be some records still left on the queue, which won't be processed.
        If nowait is False then thread will handle remaining items in queue and
        stop.
        If nowait is True then thread will be stopped even if the queue still
        contains items.
        """
        self._stop.set()
        if nowait:
            self._stop_nowait.set()
        self.queue.put_nowait(self._sentinel_item)
        if (self._thread.isAlive() and
                self._thread is not threading.currentThread()):
            self._thread.join()
        self._thread = None


class ReportPortalServiceAsync(object):
    """Wrapper around service class to transparently provide async operations
    to agents.
    """

    def __init__(self, endpoint, project, token, api_base="api/v1",
                 error_handler=None, log_batch_size=20):
        """Init the service class.

        Args:
            endpoint: endpoint of report portal service.
            project: project name to use for launch names.
            token: authorization token.
            api_base: defaults to api/v1, can be changed to other version.
            error_handler: function to be called to handle errors occurred
                during items processing (in thread)
        """
        super(ReportPortalServiceAsync, self).__init__()
        self.error_handler = error_handler
        self.log_batch_size = log_batch_size
        self.rp_client = ReportPortalService(
            endpoint, project, token, api_base)
        self.log_batch = []
        self.supported_methods = ["start_launch", "finish_launch",
                                  "start_test_item", "finish_test_item", "log"]

        self.queue = queue.Queue()
        self.listener = QueueListener(self.queue, self.process_item)
        self.listener.start()

    def terminate(self, nowait=False):
        """Finalize and stop service

        Args:
            nowait: set to True to terminate immediately and skip processing
                messages still in the queue
        """
        logger.debug("Terminating service")

        if not self.listener:
            raise Error("Service already stopped.")

        self.listener.stop(nowait)

        try:
            if not nowait:
                self._post_log_batch()
        except Exception:
            if self.error_handler:
                self.error_handler(sys.exc_info())
            else:
                raise
        finally:
            self.queue = None
            self.listener = None

    def _post_log_batch(self):
        logger.debug("Posting log batch size: %s", len(self.log_batch))
        if self.log_batch:
            try:
                self.rp_client.log_batch(self.log_batch)
            finally:
                self.log_batch = []

    def process_log(self, **log_item):
        """Special handler for log messages.

        Accumulate incoming log messages and post them in batch.
        """
        logger.debug("Processing log item: %s", log_item)
        self.log_batch.append(log_item)
        if len(self.log_batch) >= self.log_batch_size:
            self._post_log_batch()

    def process_item(self, item):
        """Main item handler.

        Called by queue listener.
        """
        logger.debug("Processing item: %s (queue size: %s)", item,
                     self.queue.qsize())
        method, kwargs = item

        if method not in self.supported_methods:
            raise Error("Not expected service method: {}".format(method))

        try:
            if method == "log":
                self.process_log(**kwargs)
            else:
                self._post_log_batch()
                getattr(self.rp_client, method)(**kwargs)
        except Exception:
            if self.error_handler:
                if not self.error_handler(sys.exc_info()):
                    self.terminate(nowait=True)
            else:
                self.terminate(nowait=True)
                raise

    def start_launch(self, name, start_time, description=None, tags=None,
                     mode=None):
        logger.debug("Start launch queued")

        args = {
            "name": name,
            "description": description,
            "tags": tags,
            "start_time": start_time,
            "mode": mode
        }
        self.queue.put_nowait(("start_launch", args))

    def finish_launch(self, end_time, status=None):
        logger.debug("Finish launch queued")

        args = {
            "end_time": end_time,
            "status": status
        }
        self.queue.put_nowait(("finish_launch", args))

    def start_test_item(self, name, start_time, item_type, description=None,
                        tags=None):
        logger.debug("start_test_item queued")

        args = {
            "name": name,
            "description": description,
            "tags": tags,
            "start_time": start_time,
            "item_type": item_type,
        }
        self.queue.put_nowait(("start_test_item", args))

    def finish_test_item(self, end_time, status, issue=None):
        logger.debug("finish_test_item queued")

        args = {
            "end_time": end_time,
            "status": status,
            "issue": issue,
        }
        self.queue.put_nowait(("finish_test_item", args))

    def log(self, time, message, level=None, attachment=None):
        """Logs a message with attachment.

        The attachment is a dict of:
            name: name of attachment
            data: file content
            mime: content type for attachment
        """
        logger.debug("log queued")

        args = {
            "time": time,
            "message": message,
            "level": level,
            "attachment": attachment,
        }
        self.queue.put_nowait(("log", args))
