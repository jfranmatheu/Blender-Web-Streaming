# INTERNAL SUBMODULE
# MODIFY IT ONLY IF YOU KNOW WHAT YOU ARE DOING
from ._register import BlenderTypes

from .reg_decorators import RegDeco
from .reg_types import RegType # , ModalFlags, PanelFlags
from .reg_helpers import RegHelper
from .property_types import PropertyTypes as Property


class ACK:
    Deco = RegDeco
    Helper = RegHelper
    Type = RegType
    Prop = Property

    # class Flag:
    #     Modal = ModalFlags # Decorator.
    #     Panel = PanelFlags # Decorator.


def clear_register_cache():
    from ._register import clear_cache
    clear_cache()
    # from .reg_types._base import BaseType
    # BaseType.clear_cache()
