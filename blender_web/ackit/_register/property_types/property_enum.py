from bpy.props import *

from typing import Tuple, List, Set, Callable
from dataclasses import dataclass, field, asdict

from ._btypes import btypes


@dataclass
class EnumPropertyHelperWrapper:
    name : str
    description : str = ""

    default : str = ""

    @property
    def ids(self) -> Set[str]:
        return {item[0] for item in self.items}

    def materialize(self) -> btypes.EnumProperty:
        if len(self.items) == 0:
            raise ValueError("'items' field must have at least one item to create an EnumProperty")
        if self.default == '':
            self.default = self.items[0][0]
        return EnumProperty(**asdict(self))


@dataclass
class EnumPropertyHelper(EnumPropertyHelperWrapper):
    items : List[Tuple[str, str, str]] = field(default_factory=list)

    def item(self, idname: str, label: str, description: str = '', icon: str = None) -> 'EnumPropertyHelper':
        if icon is not None:
            if not isinstance(icon, (str, int)):
                raise TypeError("Icon must be a string or an integer")
            self.items.append((idname, label, description, icon, len(self.items)))
        else:
            self.items.append((idname, label, description))
        return self

    def set_default(self, idname: str) -> 'EnumPropertyHelper':
        if idname not in self.ids:
            raise ValueError("Given idname not found in the provided items")
        self.default = idname
        return self


@dataclass
class DynamicEnumPropertyHelper(EnumPropertyHelperWrapper):
    items : Callable = lambda self, context: (('NONE', 'NONE', ""),)
