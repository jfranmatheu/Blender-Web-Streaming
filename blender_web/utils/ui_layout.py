from bpy.types import UILayout


def draw_section(layout: UILayout, title: str, icon: str = 'NONE', align_content: bool = False, use_property_split: bool = True) -> UILayout:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.label(text=title, icon=icon)
        content = section.box().column(align=align_content)
        content.use_property_split = use_property_split
        content.use_property_decorate = False
        return content

def draw_section_h(layout: UILayout, title: str, icon: str = 'NONE', align_content: bool = False, use_property_split: bool = True) -> tuple[UILayout, UILayout]:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.label(text=title, icon=icon)
        content = section.box().column(align=align_content)
        content.use_property_split = use_property_split
        content.use_property_decorate = False
        return header, content

def draw_section_with_tabs(layout: UILayout, data, attr: str, title: str, icon: str = 'NONE', align_content: bool = False, use_property_split: bool = True) -> UILayout:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.label(text=title, icon=icon)
        section.row(align=True).prop(data, attr, text=' ', expand=True)
        content = section.box().column(align=align_content)
        content.use_property_split = use_property_split
        content.use_property_decorate = False
        return content
