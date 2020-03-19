import sys
import logging
from contextlib import contextmanager
from functools import wraps
from six import PY2


class RPLogger(logging.getLoggerClass()):
    def __init__(self, name, level=0):
        super(RPLogger, self).__init__(name, level=level)

    def _log(self, level, msg, args,
             exc_info=None, extra=None, stack_info=False, attachment=None):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        sinfo = None
        if logging._srcfile:
            # IronPython doesn't track Python frames, so findCaller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                if PY2:
                    # In python2.7 findCaller() don't accept any parameters
                    # and returns 3 elements
                    fn, lno, func = self.findCaller()
                else:
                    fn, lno, func, sinfo = self.findCaller(stack_info)

            except ValueError:  # pragma: no cover
                fn, lno, func = '(unknown file)', 0, '(unknown function)'
        else:
            fn, lno, func = '(unknown file)', 0, '(unknown function)'

        if exc_info and not isinstance(exc_info, tuple):
            exc_info = sys.exc_info()

        if PY2:
            # In python2.7 makeRecord() accepts everything but sinfo
            record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                     exc_info, func, extra)
        else:
            record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                     exc_info, func, extra, sinfo)

        if not getattr(record, 'attachment', None):
            record.attachment = attachment
        self.handle(record)


class RPLogHandler(logging.Handler):
    # Map loglevel codes from `logging` module to ReportPortal text names:
    _loglevel_map = {
        logging.NOTSET: 'TRACE',
        logging.DEBUG: 'DEBUG',
        logging.INFO: 'INFO',
        logging.WARNING: 'WARN',
        logging.ERROR: 'ERROR',
        logging.CRITICAL: 'ERROR',
    }
    _sorted_levelnos = sorted(_loglevel_map.keys(), reverse=True)

    def __init__(self, py_test_service,
                 level=logging.NOTSET,
                 filter_reportportal_client_logs=False,
                 endpoint=None):
        super(RPLogHandler, self).__init__(level)
        self.py_test_service = py_test_service
        self.filter_reportportal_client_logs = filter_reportportal_client_logs
        self.ignored_record_names = ('reportportal_client',
                                     'pytest_reportportal')
        self.endpoint = endpoint

    def filter(self, record):
        if self.filter_reportportal_client_logs is False:
            return True
        if record.name.startswith(self.ignored_record_names):
            return False
        if record.name == 'urllib3.connectionpool':
            # Filter the reportportal_client requests instance
            # urllib3 usage
            if self.endpoint in self.format(record):
                return False
        return True

    def emit(self, record):
        msg = ''

        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)

        for level in self._sorted_levelnos:
            if level <= record.levelno:
                return self.py_test_service.post_log(
                    msg,
                    loglevel=self._loglevel_map[level],
                    attachment=record.__dict__.get('attachment', None),
                )


@contextmanager
def patching_logger_class():
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
