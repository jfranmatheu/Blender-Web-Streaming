from collections import defaultdict

import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, _node_categories

from ... import BlenderTypes
from ....globals import GLOBALS


node_categories = []
node_category_classes = {}


def get_node_category_class(node_tree_idname: str):
    return node_category_classes[node_tree_idname]


def new_node_category(node_tree_cls) -> NodeCategory:
    node_cat_class = type(
        f'{GLOBALS.ADDON_MODULE.upper()}_NodeCategory_{node_tree_cls.original_class.tree_type}',
        (NodeCategory,),
        {
            'poll': classmethod(lambda cls, ctx: ctx.space_data.tree_type == node_tree_cls.bl_idname),
            # just for sub-categories
            # 'draw': lambda item, layout, context:
        }
    )
    node_category_classes[node_tree_cls.bl_idname] = node_cat_class
    return node_cat_class


def register_node_categories_multi(identifier, cat_list, subcat_list):
    if identifier in _node_categories:
        raise KeyError("Node categories list '%s' already registered" % identifier)
        return

    # works as draw function for menus
    def draw_node_item(self, context):
        layout = self.layout
        col = layout.column(align=True)
        for item in self.category.items(context):
            if hasattr(item, 'identifier'):
                cat = item
                col.menu("NODE_MT_category_%s" % cat.identifier)
            else:
                item.draw(item, col, context)

    menu_types = []
    for cat in (subcat_list + cat_list):
        menu_type = type("NODE_MT_category_" + cat.identifier, (bpy.types.Menu,), {
            "bl_space_type": 'NODE_EDITOR',
            "bl_label": cat.name,
            "category": cat,
            "poll": cat.poll,
            "draw": draw_node_item,
        })

        menu_types.append(menu_type)

        bpy.utils.register_class(menu_type)

    def draw_add_menu(self, context):
        layout = self.layout

        for cat in cat_list:
            if cat.poll(context):
                layout.menu("NODE_MT_category_%s" % cat.identifier)

    # stores: (categories list, menu draw function, submenu types)
    _node_categories[identifier] = (cat_list + subcat_list, draw_add_menu, menu_types)


def register():
    node_classes = BlenderTypes.Node.get_classes()
    if node_classes == []:
        return

    for node_tree_cls in BlenderTypes.NodeTree.get_classes():

        _node_classes = filter(lambda node: node.tree_type == node_tree_cls.bl_idname, node_classes)

        node_cat_class = get_node_category_class(node_tree_cls.bl_idname)
        cat_node_relationship: dict[str, list] = defaultdict(list)
        subcat_node_relationship: dict[str, dict[str, list]] = defaultdict(dict)
        node_subcategories = []

        for node in _node_classes:
            if '/' in node.category:
                cat, subcat = node.category.split('/')
                cat = cat.title()
                subcat = subcat.title()
                if cat not in subcat_node_relationship or subcat not in subcat_node_relationship[cat]:
                    subcat_node_relationship[cat][subcat] = [node]
                else:
                    subcat_node_relationship[cat][subcat].append(node)
            else:
                cat_node_relationship[node.category.title()].append(node)

        for cat_name, nodes in cat_node_relationship.items():
            subcats: dict[str, list] = subcat_node_relationship.get(cat_name, {})
            node_subcats = [
                node_cat_class(
                    cat_name.upper() + '_' + subcat_name.upper().replace(' ', '_'),
                    subcat_name, # .title(),
                    items=[
                        NodeItem(subcat_node.bl_idname, label=subcat_node.bl_label) for subcat_node in subcat_items
                    ]
                )
                for (subcat_name, subcat_items) in subcats.items()
            ]
            node_subcategories.extend(node_subcats)
            node_categories.append(
                node_cat_class(
                    cat_name.upper().replace(' ', '_'),
                    cat_name, # .title(),
                    items= node_subcats +
                        # TODO: support settings... which may support several different settings... so another loop...
                        [
                            NodeItem(node.bl_idname, label=node.bl_label) for node in nodes
                        ]
                )
            )

        if node_cat_class.__name__ not in nodeitems_utils._node_categories:
            register_node_categories_multi(node_cat_class.__name__, node_categories, node_subcategories)


def unregister():
    for node_tree_cls in BlenderTypes.NodeTree.get_classes():
        node_cat_class = get_node_category_class(node_tree_cls.bl_idname)
        nodeitems_utils.unregister_node_categories(node_cat_class.__name__)
        node_categories.clear()
