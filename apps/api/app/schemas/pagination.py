from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    items: list[T]
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def build(cls, items: list[T], page: int, page_size: int, total: int) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if total else 0
        return cls(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)
