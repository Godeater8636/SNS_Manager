from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details or []})


class UnauthorizedException(AppException):
    def __init__(self, message: str = "認証が必要です"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "権限がありません"):
        super().__init__(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


class NotFoundException(AppException):
    def __init__(self, resource: str = "リソース"):
        super().__init__(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{resource}が見つかりません")


class ConflictException(AppException):
    def __init__(self, message: str = "既に存在します"):
        super().__init__(status.HTTP_409_CONFLICT, "CONFLICT", message)


class ValidationException(AppException):
    def __init__(self, message: str, details: list | None = None):
        super().__init__(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", message, details)


class PlanLimitException(AppException):
    def __init__(self, message: str = "プランの上限に達しました"):
        super().__init__(status.HTTP_403_FORBIDDEN, "PLAN_LIMIT", message)


class RateLimitException(AppException):
    def __init__(self, message: str = "レートリミットを超過しました"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", message)
