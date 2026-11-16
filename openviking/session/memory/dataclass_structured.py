# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Core domain data classes for memory system.
"""

import json
import re
from datetime import datetime
from enum import Enum
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, Field, PrivateAttr, WithJsonSchema, model_validator

from openviking.session.memory.merge_op.base import (
    FieldType,
    MergeOp,
)
from openviking.session.memory.utils.template_utils import TemplateUtils

T = TypeVar("T")


# ============================================================================
# Link Type and Link Models
# ============================================================================


LINK_TYPE_DEFAULT = "related_to"
_LINK_TYPE_RE = re.compile(r"^[a-z]+(?:_[a-z]+){0,2}$")



class DeleteId(BaseModel):
    """Delete request by page_id, optionally remapped to a replacement page_id."""

    delete_page_id: Annotated[Optional[int], WithJsonSchema({"type": "integer"})] = Field(
        ..., description="Page_id of the memory item to delete."
    )
    replacement_page_id: Annotated[
        Optional[int],
        WithJsonSchema({"anyOf": [{"type": "integer"}, {"type": "null"}]}),
    ] = Field(
        ...,
        description=(
            "Replacement page_id that should inherit this deleted page's existing links/backlinks; "
            "use null for a pure delete."
        ),
    )


class FaultTolerantBaseModel(BaseModel):
    """
    支持验证前自动容错的 BaseModel，类似 vikingdb 的 BaseModelCompat。

    在 model_validator(mode='before') 中对所有字段做类型容错处理，
    使得模型可以接受 LLM 输出的不标准格式数据。
    """

    @model_validator(mode="before")
    @classmethod
    def values_fault_tolerance(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """在验证前对所有字段做容错处理"""
        if isinstance(data, dict):
            field_types = get_type_hints(cls)
            for field_name, value in data.items():
                if field_name in field_types:
                    data[field_name] = cls.value_fault_tolerance(field_types[field_name], value)
            return data
        return {}

    @classmethod
    def get_origin_type(cls, annotation) -> type:
        """从 Optional 或 Union 类型中提取基础类型"""
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            if len(args) == 2 and args[1] is type(None):
                return cls.get_origin_type(args[0])
        elif origin is list:
            return list
        return annotation

    @classmethod
    def get_arg_type(cls, annotation) -> type:
        """从 List annotation 中提取元素类型"""
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            if len(args) == 2 and args[1] is type(None):
                return cls.get_arg_type(args[0])
        elif origin is list:
            args = get_args(annotation)
            if args:
                return args[0]
        return None

    @classmethod
    def any_to_str(cls, value) -> str:
        """将任意值转换为字符串"""
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(map(str, value))
        elif isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (int, bool, float)):
            return f"{value}"
        return str(value)

    @classmethod
    def value_fault_tolerance(cls, field_type, value):
        """
        字段级别的容错处理：
        - 'None' -> None (非 str 类型)
        - list/dict/number -> str (目标是 str)
        - str -> int/float (目标是数字)
        - str/dict -> list (目标是 list)
        - list 元素类型容错
        - 非法 LinkType -> related_to
        """
        origin_type = cls.get_origin_type(field_type)

        # json_repair 会把 None 转换成 'None'
        if value == "None" and origin_type is not str:
            return None

        if isinstance(origin_type, type) and issubclass(origin_type, Enum):
            if origin_type is LinkType:
                try:
                    return origin_type(value)
                except (ValueError, TypeError):
                    return LinkType.RELATED_TO

        if origin_type is str:
            return cls.any_to_str(value)
        elif origin_type is int:
            if isinstance(value, str):
                if value is None or value == "None":
                    return 0
                try:
                    return int(value)
                except (ValueError, TypeError):
                    pass
        elif origin_type is float:
            if isinstance(value, str):
                if value is None or value == "None":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass
        elif origin_type is list:
            if isinstance(value, str):
                return [value]
            elif isinstance(value, dict):
                return [value]
            elif isinstance(value, list):
                arg_type = cls.get_arg_type(field_type)
                if arg_type is str:
                    return [cls.any_to_str(v) for v in value]
        return value


# ============================================================================
# Memory Operations
# ============================================================================


class MemoryOperationsProtocol(Protocol):
    """Protocol for memory operations (for type checking)."""

    reasoning: str
    write_uris: List[Any]
    edit_uris: List[Any]
    delete_ids: List[DeleteId]

    def is_empty(self) -> bool: ...


class StructuredMemoryOperations(FaultTolerantBaseModel):
    """
    Fallback memory operations model with fault tolerance.

    Use SchemaModelGenerator.create_structured_operations_model() to get
    the actual type-safe implementation with per-memory_type fields.
    """

    reasoning: str = Field(
        "",
        description="reasoning",
    )
    write_uris: List[Any] = Field(
        default_factory=list,
        description="Write operations with flat data format",
    )
    edit_uris: List[Any] = Field(
        default_factory=list,
        description="Edit operations with flat data format",
    )
    delete_ids: List[DeleteId] = Field(
        default_factory=list,
        description="Delete operations by page_id, with optional replacement_page_id",
    )

    def is_empty(self) -> bool:
        """Check if there are any operations."""
        return len(self.write_uris) == 0 and len(self.edit_uris) == 0 and len(self.delete_ids) == 0

    def to_legacy_operations(self) -> Dict[str, Any]:
        """Convert to legacy format (identity for fallback)."""
        return {
            "write_uris": self.write_uris,
            "edit_uris": self.edit_uris,
            "delete_ids": self.delete_ids,
        }

    model_config = {"extra": "ignore"}


# Backward compatibility alias
MemoryOperations = StructuredMemoryOperations
