from bpy.props import *

from ._btypes import PropertyBpyTypes, btypes

from enum import Enum


class CollectionPropertyTypes(Enum):
    OBJECT = btypes.Object
    MESH = btypes.Mesh
    CAMERA = btypes.Camera
    LIGHT = btypes.Light
    ARMATURE = btypes.Armature
    NODE_TREE = btypes.NodeTree
    NODE_GROUP = btypes.NodeGroup
    BRUSH = btypes.Brush
    IMAGE = btypes.Image
    TEXTURE = btypes.Texture
    CUSTOM = None

    def __call__(self, name: str, **kwargs: dict) -> btypes.CollectionProperty:
        if self.value is None:
            if 'type' not in kwargs:
                raise AttributeError("'type' kwarg must be specified to create a - CUSTOM - CollectionProperty")
            return CollectionProperty(name=name, **kwargs)
        return CollectionProperty(type=self.value, name=name, **kwargs)
