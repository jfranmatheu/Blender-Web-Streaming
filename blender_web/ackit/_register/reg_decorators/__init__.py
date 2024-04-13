from .reg_property_group import PropertyGroupRegister
from .reg_ui_append import UIAppend
from .reg_rna_sub import subscribe_to_rna_change # RNASubscription
from .reg_timer import new_timer_as_decorator
from .reg_handlers import Handlers
from .reg_ops import OpsDecorators
from .reg_ui_override import ui_override
from .gz import RegisterGZ


class RegDeco:
    PROP_GROUP = PropertyGroupRegister
    RNA_SUB = subscribe_to_rna_change
    HANDLER = Handlers
    TIMER = new_timer_as_decorator
    UI_APPEND = UIAppend
    UI_OVERRIDE = ui_override
    OPS = OpsDecorators
    GZ = RegisterGZ
