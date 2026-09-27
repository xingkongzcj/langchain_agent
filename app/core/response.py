"""统一 API 响应格式模块。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式。

    所有接口均返回该结构：code（业务状态码）、message（提示信息）、data（业务数据）。
    状态码约定：200 成功、400 参数错误、404 不存在、500 服务器错误。
    """

    model_config = ConfigDict(from_attributes=True)

    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="业务数据")

    @classmethod
    def success(cls, data: T | None = None, message: str = "success") -> "ApiResponse[T]":
        """构造成功响应。"""
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "操作失败", data: T | None = None) -> "ApiResponse[T]":
        """构造错误响应。"""
        return cls(code=code, message=message, data=data)
