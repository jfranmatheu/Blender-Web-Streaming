from .help_shortcut import ShortcutRegister
from .help_property import PropertyRegister, BatchPropertyRegister, PropertyRegisterRuntime
from .help_ui_hide import ui_hide


class RegHelper:
    KEYMAP = ShortcutRegister
    MACRO = None # TODO: Code the helper.
    PROP = PropertyRegister
    PROP_RUNTIME = PropertyRegisterRuntime
    PROP_BATCH = BatchPropertyRegister
    UI_HIDE = ui_hide
