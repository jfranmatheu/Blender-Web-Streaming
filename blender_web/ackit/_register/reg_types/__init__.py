from ._base import BaseType

from .ops import OperatorTypes, OpsReturn, ModalFlags
from .preferences import AddonPreferences
from .ui import InterfaceTypes, PanelFlags
from .property_group import PropertyGroup
from .node_editor import NodeTree, NodeSocket, Node


class RegType:
    PREFS = AddonPreferences
    UI = InterfaceTypes
    OPS = OperatorTypes
    PROP_GROUP = PropertyGroup

    class NodeEditor:
        NODE_TREE = NodeTree
        NODE = Node
        NODE_SOCKET = NodeSocket
