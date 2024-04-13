from dataclasses import dataclass

from .event import GEvent


class OpsReturn:
    FINISH = {'FINISHED'}
    CANCEL = {'CANCELLED'}
    PASS = {'PASS_THROUGH'}
    RUN = {'RUNNING_MODAL'}
    UI = {'INTERFACE'}


def add_modal_handler(context, operator):
    if not context.window_manager.modal_handler_add(operator):
        print("WARN! Operator failed to add modal handler!")
        return OpsReturn.CANCEL
    return OpsReturn.RUN


@dataclass
class ModalEventTrigger:
    type: str
    value: str
    ctrl: bool | None = None
    alt: bool | None = None
    shift: bool | None = None

    def test_event(self) -> bool:
        return GEvent.check(self.type, self.value, shift=self.shift, alt=self.alt, ctrl=self.ctrl)
