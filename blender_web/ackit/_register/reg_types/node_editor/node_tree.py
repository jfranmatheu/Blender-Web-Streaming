import bpy
from bpy import types as bpy_types

from .._base import BaseType
from ....globals import GLOBALS

from .node import Node


node_tree_classes = {}
# node_base_classes = {}


class NodeTree(BaseType):
    ''' Base Class for NodeTree types. '''
    label: str = 'Custom NodeTree'
    icon: str = 'MONKEY'
    tree_type: str = f'{GLOBALS.ADDON_MODULE.upper()}_NodeTree_default'

    NodeType: Node

    nodes: list[Node]

    ###################################

    @classmethod
    def node(cls, deco_node_cls: Node):
        deco_node_cls.tree_type = cls.tree_type
        return deco_node_cls

    @classmethod
    def tag_register(deco_cls) -> 'NodeTree':
        node_tree = super().tag_register(
            bpy_types.NodeTree, None,
            bl_idname=deco_cls.tree_type,
            bl_label=deco_cls.label,
            bl_icon=deco_cls.icon,
            original_class=deco_cls
        )

        from .node_cats import new_node_category
        new_node_category(node_tree)

        node_tree_classes[deco_cls.tree_type] = node_tree
        return node_tree

    ########################################


    def update(self) -> None:
        # print("NodeTree::update()")
        if not hasattr(self, 'nodes'):
            print("WTF? NodeTree has no attribute 'nodes'")
            return
        if len(self.nodes) == 0:
            print("WTF? NodeTree has 0 nodes")
            return


    #########################################

