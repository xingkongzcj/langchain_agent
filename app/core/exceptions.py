"""全局异常捕获模块。"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.response import ApiResponse

logger = logging.getLogger(__name__)


class BusinessException(Exception):
    """业务异常，用于在服务层主动抛出可预期的业务错误。"""

    def __init__(self, code: int = 400, message: str = "业务处理失败"):
        self.code = code
        self.message = message
        super().__init__(message)


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException 异常。"""
    logger.warning("HTTP 异常: status=%s, detail=%s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(code=exc.status_code, message=str(exc.detail)).model_dump(),
    )


async def business_exception_handler(_request: Request, exc: BusinessException) -> JSONResponse:
    """处理业务异常。"""
    logger.warning("业务异常: code=%s, message=%s", exc.code, exc.message)
    return JSONResponse(
        status_code=200,
        content=ApiResponse.error(code=exc.code, message=exc.message).model_dump(),
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数校验异常。"""
    logger.warning("请求参数校验失败: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content=ApiResponse.error(
            code=422,
            message="请求参数验证失败",
            data=jsonable_encoder(exc.errors()),
        ).model_dump(),
    )


async def general_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的通用异常。"""
    logger.exception("服务器内部错误: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=500, message="服务器内部错误").model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
