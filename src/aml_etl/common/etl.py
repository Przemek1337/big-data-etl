from collections.abc import Iterator
from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
R_co = TypeVar("R_co", covariant=True)


class Extractor(Protocol[T_co]):
    def extract(self) -> Iterator[T_co]: ...


class Transformer(Protocol[T_contra, R_co]):
    def transform(self, item: T_contra) -> R_co: ...


class Loader(Protocol[T_contra, R_co]):
    def load(self, item: T_contra) -> R_co: ...


class Job(Protocol):
    def run(self) -> None: ...
