from bpy.utils import register_class, unregister_class, register_classes_factory

from enum import Enum, auto
from typing import Dict, List, Type, Callable
from collections import defaultdict
from dataclasses import dataclass

from ..globals import GLOBALS
from ..debug import print_debug
from .reg_types.ops import Operator
from .reg_types import BaseType


@dataclass
class RegisterFactory:
    register: Callable
    unregister: Callable


class BlenderTypes(Enum):
    ''' Supported types. '''
    Operator = auto()
    Macro = auto()
    Menu = auto()
    Panel = auto()
    PropertyGroup = auto()
    AddonPreferences = auto()
    NodeTree = auto()
    NodeSocket = auto()
    Node = auto()

    def get_classes(self) -> List[BaseType]:
        return classes_per_type[self]
    
    def get_classes_by_module(self, module_path: str) -> List[BaseType]:
        return [cls for cls in classes_per_type[self] if module_path in cls.__module__]

    def sort_classes(self, filter: Callable) -> None:
        classes_per_type[self] = filter(self.get_classes())

    def add_class(self, cls: BaseType) -> None:
        ### print_debug(f"--> Add-Class '{cls.__name__}' of type '{self.name}', {id(cls)}")
        classes_per_type[self].append(cls)

        if GLOBALS.get_addon_global_value('IS_INITIALIZED', False):
            print_debug(
                f"[ACKit] (+) Runtime-Register {self.name} class: {cls.__name__}, {id(cls)}"
            )
            register_class(cls)

    def register_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            print_debug(f"+ Register {self.name} classes")
            reg_factory.register()
        else:
            for cls in classes_per_type[self]:
                if "bl_rna" in cls.__dict__:
                    print_debug(
                        f"[ACKit] WARN! Trying to register an already registered class: {cls.__name__}, {id(cls)}"
                    )
                    continue
                print_debug(f"[ACKit] (+) Register {self.name} class: {cls.__name__}, {id(cls)}")
                register_class(cls)

    def unregister_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            reg_factory.unregister()
        else:
            for cls in classes_per_type[self]:
                if "bl_rna" not in cls.__dict__:
                    print_debug(
                        f"[ACKit] WARN! Trying to unregister a class that is not registered: {cls.__name__}, {id(cls)}"
                    )
                    continue
                print_debug(
                    f"[ACKit] (-) UnRegister {self.name} class: {cls.__name__}, {id(cls)}"
                )
                unregister_class(cls)

    def create_classes_factory(self):
        register_factory[self] = RegisterFactory(*register_classes_factory(classes_per_type[self]))


classes_per_type: Dict[BlenderTypes, List[Type]] = defaultdict(list)
register_factory: Dict[BlenderTypes, RegisterFactory] = {}


def clear_cache():
    classes_per_type.clear()
    register_factory.clear()


def init_post():
    # Ensure that property group classes are correctly sorted to avoid dependency issues.
    from ...auto_load import get_ordered_pg_classes_to_register
    BlenderTypes.PropertyGroup.sort_classes(get_ordered_pg_classes_to_register)

    # for btype in BlenderTypes:
    #     btype.create_classes_factory()


def register():
    for btype in BlenderTypes:
        btype.register_classes()


def unregister():
    for btype in BlenderTypes:
        btype.unregister_classes()

    # Well, we can't do this in development env or BUG-s... BUG-s everywhere.
    if GLOBALS.check_in_production():
        # FUCKING BLENDER EXTENSION MESSING UP ALL... SO WE CAN'T CLEANUP CACHE BECAUSE FIRST TIME IS NOT DETECTED AS IN_DEVELOPMENT :/
        clear_cache()
