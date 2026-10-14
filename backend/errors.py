"""Central error types and stable response codes."""


class ErrorCode:
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_INVALID_RESPONSE = "AI_INVALID_RESPONSE"
    DB_UNAVAILABLE = "DB_UNAVAILABLE"
    INVALID_DOCUMENT = "INVALID_DOCUMENT"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(self, detail: str, code: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


class AIUnavailableError(AppError):
    def __init__(self, detail: str = "Sorry, the AI service is temporarily unavailable. Please try again."):
        super().__init__(detail, ErrorCode.AI_UNAVAILABLE, 503)


class AITimeoutError(AppError):
    def __init__(self, detail: str = "The AI service took too long to respond. Please try again."):
        super().__init__(detail, ErrorCode.AI_TIMEOUT, 504)


class AIInvalidResponseError(AppError):
    def __init__(self, detail: str = "The AI service returned an invalid response."):
        super().__init__(detail, ErrorCode.AI_INVALID_RESPONSE, 502)


class DBUnavailableError(AppError):
    def __init__(self, detail: str = "Database is temporarily unavailable. Please try again."):
        super().__init__(detail, ErrorCode.DB_UNAVAILABLE, 503)


class InvalidDocumentError(AppError):
    def __init__(self, detail: str):
        super().__init__(detail, ErrorCode.INVALID_DOCUMENT, 400)


class UploadFailedError(AppError):
    def __init__(self, detail: str = "Upload failed. Please try again."):
        super().__init__(detail, ErrorCode.UPLOAD_FAILED, 500)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Invalid authentication credentials"):
        super().__init__(detail, ErrorCode.UNAUTHORIZED, 401)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "You don't have permission to do this."):
        super().__init__(detail, ErrorCode.FORBIDDEN, 403)


class NotFoundError(AppError):
    def __init__(self, detail: str = "The requested resource was not found."):
        super().__init__(detail, ErrorCode.NOT_FOUND, 404)


class ValidationError(AppError):
    def __init__(self, detail: str = "Invalid request. Please check your input."):
        super().__init__(detail, ErrorCode.VALIDATION_ERROR, 422)


class InternalError(AppError):
    def __init__(self, detail: str = "Something went wrong on our side."):
        super().__init__(detail, ErrorCode.INTERNAL_ERROR, 500)
