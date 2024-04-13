# trunk-ignore(ruff/F401)
import bpy
from bpy import types as bpy_types

from .....utils.operator import OpsReturn
from .._base import BaseType


op_idname_cache = {}


class Operator(BaseType):
    """Base Class for Operator types.
    Class Properties:
        - 'label': aka bl_label.
    Class Methods:
        - 'tag_register': creates an Operator type class and tags it for registration.
        - 'run': to run this operator. (classmethod)
        - 'run_invoke': to run this operator but with invoke execution context. (classmethod)
        - 'draw_in_layout': to draw a button in the UI for this operator. (classmethod)
        - 'invoke': the Operator.invoke method, it calls execute by default.
        - 'execute': the Operator.execute method, it calls the action method by default.
        - 'action': a fast way to perform any action you need, does not requires to return OpsReturn manually.
    """

    bl_idname: str
    bl_label: str
    bl_description: str
    bl_options: set[str]
    bl_property: str

    label: str
    tooltip: str

    @classmethod
    def poll(cls, context: bpy_types.Context) -> bool:
        return True

    def invoke(self, context: bpy_types.Context, event: bpy_types.Event) -> OpsReturn:
        # print("BaseOperator::invoke() -> ", self.bl_idname)
        return self.execute(context)

    def action(self, context: bpy_types.Context) -> None:
        # print("BaseOperator::action() -> ", self.bl_idname)
        pass

    def execute(self, context: bpy_types.Context) -> OpsReturn:
        # print("BaseOperator::execute() -> ", self.bl_idname)
        if res := self.action(context):
            if isinstance(res, set):
                return res
            if isinstance(res, int):
                if res == -1:
                    return OpsReturn.CANCEL
                elif res == 0:
                    return OpsReturn.FINISH
        return OpsReturn.FINISH

    def report_debug(self, message: str) -> None:
        self.report({"DEBUG"}, message)

    def report_info(self, message: str) -> None:
        self.report({"INFO"}, message)

    def report_warning(self, message: str) -> None:
        self.report({"WARNING"}, message)

    def error(self, message: str) -> None:
        self.report({"ERROR"}, message)
        return OpsReturn.CANCEL

    def error_invalid_context(self, message: str = "Invalid Context") -> None:
        self.report({"ERROR_INVALID_CONTEXT"}, message)
        return OpsReturn.CANCEL

    def error_invalid_input(self, message: str = "Invalid Input") -> None:
        self.report({"ERROR_INVALID_INPUT"}, message)
        return OpsReturn.CANCEL

    ###################################

    @classmethod
    def tag_register(deco_cls, **kwargs: dict) -> "Operator":
        return super().tag_register(
            bpy_types.Operator,
            "OT",
            **kwargs,
        )

    @classmethod
    def run(cls, **operator_properties: dict) -> None:
        # trunk-ignore(bandit/B307)
        eval("bpy.ops." + cls.bl_idname)(**operator_properties)

    @classmethod
    def run_invoke(cls, **operator_properties: dict) -> None:
        # trunk-ignore(bandit/B307)
        eval("bpy.ops." + cls.bl_idname)("INVOKE_DEFAULT", **operator_properties)

    @classmethod
    def draw_in_layout(
        cls,
        layout: bpy_types.UILayout,
        label: str = None,
        op_props: dict | None = None,
        **draw_kwargs: dict,
    ) -> bpy_types.OperatorProperties:
        op = layout.operator(
            cls.bl_idname, text=label if label is not None else cls.label, **draw_kwargs
        )
        if op_props:
            for key, value in op_props.items():
                setattr(op, key, value)
        return op
