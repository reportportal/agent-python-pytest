"""RPLogger class for low-level logging in tests."""

import logging
import threading
from contextlib import contextmanager
from functools import wraps

from reportportal_client._local import current, set_current
from reportportal_client import RPLogger
from reportportal_client.core.worker import APIWorker


def is_api_worker(target):
    """Check if target is an RP worker thread."""
    if target:
        method_name = getattr(target, '__name__', None)
        method_self = getattr(target, '__self__', None)
        if method_name == '_monitor' and method_self:
            clazz = getattr(method_self, '__class__', None)
            if clazz is APIWorker:
                return True
    return False


@contextmanager
def patching_thread_class(config):
    """
    Add patch for Thread class.

    Set the parent thread client as the child thread's local client
    """
    if not config.rp_thread_logging:
        # Do nothing
        yield
    else:
        original_start = threading.Thread.start
        original_run = threading.Thread.run
        try:
            def wrap_start(original_func):
                @wraps(original_func)
                def _start(self, *args, **kwargs):
                    """Save the invoking thread's client if there is one."""
                    # Prevent an endless loop of workers being spawned
                    target = getattr(self, '_target', None)
                    if not is_api_worker(self) and not is_api_worker(target):
                        current_client = current()
                        self.parent_rp_client = current_client
                    return original_func(self, *args, **kwargs)

                return _start

            def wrap_run(original_func):
                @wraps(original_func)
                def _run(self, *args, **kwargs):
                    """Create a new client for the invoked thread."""
                    client = None
                    if (
                        hasattr(self, "parent_rp_client")
                        and self.parent_rp_client
                        and not current()
                    ):
                        parent = self.parent_rp_client
                        client = parent.clone()
                        client.start()
                    try:
                        return original_func(self, *args, **kwargs)
                    finally:
                        if client:
                            # Stop the client and remove any references
                            client.terminate()
                            self.parent_rp_client = None
                            del self.parent_rp_client
                            set_current(None)

                return _run

            if not hasattr(threading.Thread, "patched"):
                # patch
                threading.Thread.patched = True
                threading.Thread.start = wrap_start(original_start)
                threading.Thread.run = wrap_run(original_run)
            yield

        finally:
            if hasattr(threading.Thread, "patched"):
                threading.Thread.start = original_start
                threading.Thread.run = original_run
                del threading.Thread.patched


@contextmanager
def patching_logger_class():
    """
    Add patch for RPLogger class.

    Updated attachment in logs
    :return: wrapped function
    """
    logger_class = logging.getLoggerClass()
    original_log = logger_class._log
    original_makeRecord = logger_class.makeRecord

    try:
        def wrap_log(original_func):
            @wraps(original_func)
            def _log(self, *args, **kwargs):
                attachment = kwargs.pop('attachment', None)
                if attachment is not None:
                    kwargs.setdefault('extra', {}).update(
                        {'attachment': attachment})
                return original_func(self, *args, **kwargs)

            return _log

        def wrap_makeRecord(original_func):
            @wraps(original_func)
            def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                           func=None, extra=None, sinfo=None):
                if extra is not None:
                    attachment = extra.pop('attachment', None)
                else:
                    attachment = None
                try:
                    # Python 3.5
                    record = original_func(self, name, level, fn, lno, msg,
                                           args, exc_info, func=func,
                                           extra=extra, sinfo=sinfo)
                except TypeError:
                    # Python 2.7
                    record = original_func(self, name, level, fn, lno, msg,
                                           args, exc_info, func=func,
                                           extra=extra)
                record.attachment = attachment
                return record

            return makeRecord

        if not issubclass(logger_class, RPLogger):
            logger_class._log = wrap_log(logger_class._log)
            logger_class.makeRecord = wrap_makeRecord(logger_class.makeRecord)
            logging.setLoggerClass(RPLogger)
        yield

    finally:
        if not issubclass(logger_class, RPLogger):
            logger_class._log = original_log
            logger_class.makeRecord = original_makeRecord
            logging.setLoggerClass(logger_class)
