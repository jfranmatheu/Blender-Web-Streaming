from enum import Enum, auto

from bpy.types import Panel, Operator


class PanelFlags(Enum):
    HIDE_HEADER = auto()
    DEFAULT_CLOSED = auto()
    INSTANCED = auto()

    def __call__(self, deco_cls: Panel):
        deco_cls.panel_flags.add(self)
        return deco_cls


class ModalFlags(Enum):
    class Raycast(Enum):
        BVHTREE = auto()
        SCENE = auto()
        OBJECT = auto()

    DRAW_2D = auto()
    DRAW_3D = auto()

    def __call__(self, deco_cls: Operator):
        deco_cls.modal_flags.add(self)
        return deco_cls
