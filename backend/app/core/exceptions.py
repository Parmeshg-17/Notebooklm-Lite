from typing import Any, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: Optional[Any] = None):
        detail = f"{resource} with identifier '{identifier}' not found" if identifier is not None else resource
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Invalid credentials or token expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


AuthenticationException = UnauthorizedException


class ForbiddenException(AppException):
    def __init__(self, detail: str = "You do not have permission to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ConflictException(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class BadRequestException(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

