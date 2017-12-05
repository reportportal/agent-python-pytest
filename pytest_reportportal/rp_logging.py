import sys
import logging
from functools import wraps

from .service import PyTestService


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
                fn, lno, func, sinfo = self.findCaller(stack_info)
            except ValueError:  # pragma: no cover
                fn, lno, func = '(unknown file)', 0, '(unknown function)'
        else:
            fn, lno, func = '(unknown file)', 0, '(unknown function)'

        if exc_info and not isinstance(exc_info, tuple):
            exc_info = sys.exc_info()

        record = self.makeRecord(
            self.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
        )
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

    def __init__(self, level=logging.NOTSET,
                 filter_reportportal_client_logs=False):
        super(RPLogHandler, self).__init__(level)
        self.filter_reportportal_client_logs = filter_reportportal_client_logs

    def filter(self, record):
        if self.filter_reportportal_client_logs is False:
            return True
        if record.name.startswith('reportportal_client'):
            # Don't send reportportal_client logs.
            # Specially because we'll hit a max recursion issue
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
                break

        return PyTestService.post_log(
            msg,
            loglevel=self._loglevel_map[level],
            attachment=record.__dict__.get('attachment', None),
        )


def patch_logger_class():
    logger_class = logging.getLoggerClass()

    def wrap_log(original_func):
        @wraps(original_func)
        def _log(self, *args, **kwargs):
            attachment = kwargs.pop('attachment', None)
            if attachment is not None:
                kwargs.setdefault('extra', {}).update({'attachment': attachment})
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
                record = original_func(self, name, level, fn, lno, msg, args,
                                       exc_info, func=func, extra=extra,
                                       sinfo=sinfo)
            except TypeError:
                # Python 2.7
                record = original_func(self, name, level, fn, lno, msg, args,
                                       exc_info, func=func, extra=extra)
            record.attachment = attachment
            return record
        return makeRecord

    # Store references to the original methods to allow unpatching
    setattr(logger_class, '_original__log', logger_class._log)
    logger_class._log = wrap_log(logger_class._log)
    setattr(logger_class, '_original_makeRecord', logger_class.makeRecord)
    logger_class.makeRecord = wrap_makeRecord(logger_class.makeRecord)


def unpatch_logger_class():
    logger_class = logging.getLoggerClass()
    if hasattr(logger_class, '_original__log'):
        logger_class._log = logger_class._original__log
        delattr(logger_class, '_original__log')
    if hasattr(logger_class, '_original_makeRecord'):
        logger_class.makeRecord = logger_class._original_makeRecord
        delattr(logger_class, '_original_makeRecord')
