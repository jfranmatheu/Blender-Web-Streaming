import bpy
from bpy import types as bpy_types

from uuid import uuid4

from .._base import BaseType
from ....globals import GLOBALS
from ...property_types import PropertyTypes as Property


class Node(BaseType):
    label: str = 'Custom Node'
    tooltip: str = 'Custom Node Tooltip'
    icon: str = 'NONE'
    category: str = 'Unasigned'

    tree_type: str = f'{GLOBALS.ADDON_MODULE.upper()}_NodeTree_default'


    ###################################

    @classmethod
    def tag_register(deco_cls) -> 'Node':
        node_idname = f'{GLOBALS.ADDON_MODULE.upper()}_Node_{deco_cls.__name__}'

        node = super().tag_register(
            bpy_types.Node, 'Node',
            bl_idname=node_idname,
            bl_description=deco_cls.tooltip,
            bl_label=deco_cls.label,
            bl_icon=deco_cls.icon,
        )

        return node


    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Node type functions.
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    @classmethod
    def poll(cls, ntree: bpy_types.NodeTree) -> bool:
        return ntree.bl_idname == cls.tree_type

    def init(self, context: bpy_types.Context):
        self.uuid = uuid4().hex
        # self.dirty = True

        print("New node ", self)

    # Copy function to initialize a copied node from an existing one.
    def copy(self, node: 'Node'):
        self.uuid = uuid4().hex
        # self.dirty = True
        print("Copying from node ", node)

    # Free function to clean up on removal.
    def free(self):
        print("Removing node ", self, ", Goodbye!")


    ###################################

    @property
    def node_tree(self):
        from .node_tree import NodeTree
        node_tree: NodeTree = self.id_data
        return node_tree

    uuid: Property.STRING(name='Node UUID')
    # dirty: Property.STRING(name='Node Dirty State')
