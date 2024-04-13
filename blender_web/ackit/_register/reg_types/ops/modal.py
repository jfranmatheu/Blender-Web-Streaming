from enum import Enum, auto

from bpy import types as bpy_types

from .....utils.event import Mouse, EventType, EventValue, set_global_event, GEvent
from .....utils.cursor import CursorIcon
from .....utils.operator import ModalEventTrigger
from .operator import Operator, OpsReturn


class ModalFlags(Enum):
    ''' Use as decorator over an Operator subclass. '''
    class Raycast(Enum):
        BVHTREE = auto()
        SCENE = auto()
        OBJECT = auto()

    DRAW_2D = auto()
    DRAW_3D = auto()

    def __call__(self, deco_cls: 'ModalOperator'):
        deco_cls.modal_flags.add(self)
        return deco_cls


active_modal_instance: dict['ModalOperator', 'ModalOperator'] = {}


class ModalOperator(Operator):
    # Blender props.
    bl_cursor_pending: str

    # --------------------------------
    # Properties you should set in your subclasses.
    modal_flags: set[ModalFlags]

    # --------------------------------

    modal_use_timer: bool = False

    modal_cursor: CursorIcon | None = None

    modal_cancel_events: tuple[ModalEventTrigger] = (
        ModalEventTrigger(EventType.ESC, EventValue.ANY),
        ModalEventTrigger(EventType.RIGHTMOUSE, EventValue.ANY),
    )
    modal_finish_events: tuple[ModalEventTrigger] = ()

    mouse: Mouse

    # --------------------------------
    # Props and methods useful to access and manipulate active modal operator externally.
    is_modal_running: bool = False
    signals: set[str]

    @classmethod
    def stop_instance(cls, cancel: bool = True):
        if instance := active_modal_instance.get(cls, None):
            instance.add_signal(signal_id='CANCEL' if cancel else 'FINISH')

    @classmethod
    def add_signal(self, signal_id: str) -> None:
        self.signals.add(signal_id)

    # --------------------------------

    def invoke(self, context: bpy_types.Context, event: bpy_types.Event) -> OpsReturn:
        # print("BaseOperator::invoke() -> ", self.bl_idname)
        if not context.window_manager.modal_handler_add(self):
            return OpsReturn.CANCEL
        self.mouse = Mouse.init(event)
        self.event_start_type = event.type
        set_global_event(event)
        if self.modal_use_timer:
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        if self.modal_cursor is not None:
            context.window.cursor_modal_set(self.modal_cursor.name)
        self.__class__.is_modal_running = True
        global active_modal_instance
        active_modal_instance[self.__class__] = self
        self.signals = set()
        self.modal_start(context)
        return OpsReturn.RUN

    def modal(self, context: bpy_types.Context, event: bpy_types.Event) -> OpsReturn:
        # Signals.
        while len(self.signals) != 0:
            signal = self.signals.pop()
            if 'CANCEL' in signal:
                self._modal_end(context, cancel=True)
                return OpsReturn.CANCEL
            if 'FINISH' in signal:
                self._modal_end(context, cancel=False)
                return OpsReturn.FINISH
            self.process_signal(context, signal)

        # Update GEvent.
        set_global_event(event)

        # Modal Triggers.
        for event_trigger in self.modal_cancel_events:
            if event_trigger.test_event():
                self._modal_end(context, cancel=True)
                return OpsReturn.CANCEL
        for event_trigger in self.modal_finish_events:
            if event_trigger.test_event():
                self._modal_end(context, cancel=False)
                return OpsReturn.FINISH

        # Special Event callbacks (mouse motion, timer...)
        if event.type in {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
            self.mouse.update(event)
            res = self.modal__mouse_move(context, self.mouse)
        elif self.modal_use_timer and event.type in {EventType.TIMER}:
            res = self.modal_timer(context)
        else:
            # Generic modal event handling.
            res = self.modal_update(context)

        # Handle modal callbacks result.
        if isinstance(res, set):
            if 'CANCELLED' in res:
                self._modal_end(context, cancel=True)
            if 'FINISHED' in res:
                self._modal_end(context, cancel=False)
            return res
        if isinstance(res, int):
            if res == -1:
                self._modal_end(context, cancel=True)
                return OpsReturn.CANCEL
            if res == 0:
                self._modal_end(context, cancel=False)
                return OpsReturn.FINISH
        return OpsReturn.RUN

    def process_signal(self, context: bpy_types.Context, signal: str) -> None:
        pass

    def modal_start(self, context: bpy_types.Context) -> None:
        pass

    def modal_timer(self, context: bpy_types.Context) -> None:
        pass

    def modal_update(self, context: bpy_types.Context) -> OpsReturn:
        return OpsReturn.RUN

    def modal__mouse_move(self, context: bpy_types.Context, mouse: Mouse) -> None:
        pass

    def _modal_end(self, context: bpy_types.Context, cancel: bool) -> None:
        if self.modal_cursor is not None:
            context.window.cursor_modal_restore()
        if self.modal_use_timer:
            context.window_manager.event_timer_remove(self._timer)
        self.modal_end(context, cancel=cancel)

        self.__class__.is_modal_running = False
        global active_modal_instance
        del active_modal_instance[self.__class__]
        del self.signals
        del self.mouse

    def modal_end(self, context: bpy_types.Context, cancel: bool) -> None:
        pass

    def execute(self, context: bpy_types.Context) -> OpsReturn:
        return OpsReturn.CANCEL

    #############################

    @classmethod
    def tag_register(deco_cls, flags: set[ModalFlags] = set()) -> 'ModalOperator':
        return super().tag_register()
