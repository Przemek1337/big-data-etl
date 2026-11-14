from collections.abc import Iterator
from typing import Any


def _children(component: Any) -> list[Any]:
    children = getattr(component, "children", None)
    if children is None:
        return []
    if isinstance(children, list | tuple):
        return list(children)
    return [children]


def walk(component: Any) -> Iterator[Any]:
    yield component
    for child in _children(component):
        yield from walk(child)


def collect_text(component: Any) -> str:
    parts = [str(node) for node in walk(component) if isinstance(node, str | int | float)]
    return " ".join(parts)


def find_by_class(component: Any, class_name: str) -> list[Any]:
    wanted = set(class_name.split())
    return [
        node
        for node in walk(component)
        if wanted and wanted <= set(str(getattr(node, "className", "") or "").split())
    ]


def find_by_type(component: Any, type_name: str) -> list[Any]:
    return [node for node in walk(component) if type(node).__name__ == type_name]
