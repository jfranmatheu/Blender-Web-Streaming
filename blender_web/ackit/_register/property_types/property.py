from bpy.props import *

from .property_enum import EnumPropertyHelper, DynamicEnumPropertyHelper
from .property_pointer import PointerPropertyTypes

from mathutils import Matrix

IdentityMatrix_2 = Matrix.Identity(2)
IdentityMatrix_3 = Matrix.Identity(3)
IdentityMatrix_4 = Matrix.Identity(4)


class PropertyTypes:
    FLOAT = FloatProperty
    INT = IntProperty
    BOOL = BoolProperty
    FLOAT_VECTOR = FloatVectorProperty
    INT_VECTOR = IntVectorProperty
    BOOL_VECTOR = BoolVectorProperty
    ENUM = EnumProperty
    STRING = StringProperty
    POINTER_CUSTOM = PointerProperty

    ANGLE_DEGREE = lambda name, default = 0, **kwargs: FloatProperty(name=name, default=default, min=0, max=360, subtype='ANGLE', unit='ROTATION', **kwargs)
    FACTOR = lambda name, default_value = 0, **kwargs: FloatProperty(name=name, default=default_value, min=0, max=1, **kwargs)

    IVECTOR_2 = lambda default_vector = (0, 0), **kwargs: IntVectorProperty(default=default_vector, size=2, **kwargs)
    IVECTOR_3 = lambda default_vector = (0, 0, 0), **kwargs: IntVectorProperty(default=default_vector, size=3, **kwargs)
    IVECTOR_N = lambda default_vector, **kwargs: IntVectorProperty(default=default_vector, size=len(default_vector), **kwargs)
    VECTOR_2 = lambda default_vector, **kwargs: FloatVectorProperty(default=default_vector, size=2, **kwargs)
    VECTOR_3 = lambda default_vector, **kwargs: FloatVectorProperty(default=default_vector, size=3, **kwargs)
    VECTOR_N = lambda default_vector, **kwargs: FloatVectorProperty(default=default_vector, size=len(default_vector), **kwargs)

    COLOR_RGB = lambda name, default_color, **kwargs: FloatVectorProperty(name=name, default=default_color, min=0.0, max=1.0, size=3, subtype='COLOR', **kwargs)
    COLOR_RGBA = lambda name, default_color, **kwargs: FloatVectorProperty(name=name, default=default_color, min=0.0, max=1.0, size=4, subtype='COLOR', **kwargs)

    MATRIX_2 = lambda name, **kwargs: FloatVectorProperty(name=name, default=IdentityMatrix_2, size=(2, 2), **kwargs)
    MATRIX_3 = lambda name, **kwargs: FloatVectorProperty(name=name, default=IdentityMatrix_3, size=(3, 3), **kwargs)
    MATRIX_4 = lambda name, **kwargs: FloatVectorProperty(name=name, default=IdentityMatrix_4, size=(4, 4), **kwargs)
    MATRIX_N = lambda name, default_matrix, **kwargs: FloatVectorProperty(name=name, default=default_matrix, size=(len(default_matrix), len(default_matrix[0])), **kwargs)

    DIRPATH = lambda **kwargs: StringProperty(subtype='DIR_PATH', **kwargs)
    FILEPATH = lambda **kwargs: StringProperty(subtype='FILE_PATH', **kwargs)

    POINTER = PointerPropertyTypes
    COLLECTION = lambda type, **kwargs: CollectionProperty(type=type, **kwargs)

    ENUM_HELPER = EnumPropertyHelper
    ENUM_DYNAMIC = DynamicEnumPropertyHelper
