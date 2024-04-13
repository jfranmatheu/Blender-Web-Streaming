from typing import Type, Dict, List
from dataclasses import dataclass
from collections import defaultdict

from ..property_types import PropertyTypes
from ...globals import GLOBALS


@dataclass
class PropertyWrapper:
    prop_name: str
    property: Type
    remove_on_unregister: bool


to_register_properties: Dict[Type, List[PropertyWrapper]] = defaultdict(list)


def PropertyRegister(data, prop_name, property: PropertyTypes, remove_on_unregister: bool = True) -> None:
    to_register_properties[data].append(PropertyWrapper(prop_name, property, remove_on_unregister))

def PropertyRegisterRuntime(data, prop_name, property: PropertyTypes) -> None:
    setattr(data, prop_name, property)

def BatchPropertyRegister(data, **props: dict) -> None:
    to_register_properties[data].extend(
        [
            PropertyWrapper(prop_name, property)
            for prop_name, property in props.items()
        ]
    )


def register_post():
    for data, props in to_register_properties.items():
        for prop_wrap in props:
            setattr(data, prop_wrap.prop_name, prop_wrap.property)

def unregister():
    for data, props in to_register_properties.items():
        for prop_wrap in props:
            if prop_wrap.remove_on_unregister:
                delattr(data, prop_wrap.prop_name)
    
    if GLOBALS.check_in_production():
        to_register_properties.clear()
