
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str):
        self.detail = detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class DuplicateError(AppError):
    status_code = status.HTTP_409_CONFLICT


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class InvalidReferenceError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
