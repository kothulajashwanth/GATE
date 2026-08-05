from typing import Annotated

from fastapi import Query

PaginateParams = Annotated[
    int,
    Query(ge=1, le=100, description="Page size"),
]

PageParams = Annotated[
    int,
    Query(ge=1, description="Page number"),
]
