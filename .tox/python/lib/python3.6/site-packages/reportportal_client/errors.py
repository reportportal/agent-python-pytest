class Error(Exception):
    """General exception for package."""


class ResponseError(Error):
    """Error in response returned by RP"""


class EntryCreatedError(ResponseError):
    """Represents error in case no entry is created.

    No 'id' in the json response.
    """


class OperationCompletionError(ResponseError):
    """Represents error in case of operation failure.

    No 'msg' in the json response.
    """
