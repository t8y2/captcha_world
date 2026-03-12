# generators package
from .base import BaseGenerator

REGISTRY: dict[str, type] = {}

def register(name: str):
    def deco(cls):
        REGISTRY[name] = cls
        return cls
    return deco

from . import (
    slide, geometry_click, rotation_match,
    coordinates, click_order,
)
