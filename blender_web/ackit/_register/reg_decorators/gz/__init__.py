_types = []


def RegisterGZ(supported_spaces: set[str], use_singleton: bool = True):
    def wrapper(cls):
        from .gz import BWS_BaseGZ
        from .gzg import BWS_BaseGZG
        from .km import BWS_GZGKM
        gz_type = type(
            f"BWS_GZ_{cls.__name__}",
            (BWS_BaseGZ,),
            {
                'bl_idname': f"BWS_GZ_{cls.__name__.lower()}",
                'data_type': cls,
                'use_singleton': use_singleton
            }
        )
        _types.append(gz_type)
        for space_type in supported_spaces:
            gzg_type = type(
                f"BWS_GZG_{cls.__name__}_{space_type}",
                (BWS_BaseGZG, BWS_GZGKM),
                {
                    'bl_idname': f"BWS_GZG_{cls.__name__.lower()}_{space_type.lower()}",
                    'bl_label': "{cls.__name__} GZG",
                    'bl_space_type': space_type,
                    'gz_type': gz_type
                }
            )
            _types.append(gzg_type)
        return cls
    return wrapper


def register():
    from bpy.utils import register_class
    for cls in _types: register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in _types: unregister_class(cls)
