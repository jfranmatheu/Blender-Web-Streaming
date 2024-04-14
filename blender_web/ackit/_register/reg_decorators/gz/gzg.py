#from ...reg_types import BaseType


class BWS_BaseGZG:#(BaseType):

    #@classmethod
    #def tag_register(cls):
    #    return super().tag_register('GizmoGroup', 'GZG')

    # ----------------------------------------------------------------

    bl_region_type: str = 'WINDOW'
    bl_options: set[str] = {'PERSISTENT', 'SHOW_MODAL_ALL'}
    gz_type = None

    def setup(gzg, context):
        # print("TheAPGZG::setup")
        gzg.gz_type.get_data(context) # force init data.
        gz = gzg.gz_type.get_gz(gzg)
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1.0
        gzg.gz = gz

    @classmethod
    def poll(cls, context) -> bool: return cls.gz_type.data_type._poll(context, cls.gz_type.get_data(context))
    def invoke_prepare(gzg, context, gz) -> None: gz.get_data(context)._invoke_prepare(context)
    def draw_prepare(gzg, context): gzg.gz_type.get_data(context)._draw_prepare(context)
    def refresh(gzg, context): gzg.gz_type.get_data(context)._refresh(context)
