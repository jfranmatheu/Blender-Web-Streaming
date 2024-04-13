from bpy.types import UILayout, Context

from .._base import BaseType


class DrawExtension:
    def section(self,
                layout: UILayout,
                title: str,
                icon: str = 'NONE',
                header_scale: float = 0.8,
                content_scale: float = 1.2) -> tuple[UILayout, UILayout]:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.scale_y = header_scale
        header.label(text=title, icon=icon)
        content = section.box().column()
        content.scale_y = content_scale
        return header, content

    def row_scale(self, layout: UILayout, scale: float = 1.4) -> UILayout:
        row = layout.row()
        row.scale_y = scale
        return row


class BaseUI(BaseType):
    layout: UILayout
    bl_idname: str
    bl_label: str

    @property
    def layout(self) -> UILayout:
        return self.layout

    def draw(self, context: Context):
        self.draw_ui(context, self.layout)

    def draw_ui(self, context: Context, layout: UILayout):
        pass

    ###################################

    @classmethod
    def draw_in_layout(cls, layout: UILayout) -> None:
        pass
