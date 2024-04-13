class BWS_BaseGZG:
    bl_region_type: str = 'WINDOW'
    bl_options: set[str] = {'PERSISTENT', 'SHOW_MODAL_ALL'}
    gz_type = None

    def setup(gzg):
        # print("TheAPGZG::setup")
        gz = gzg.gz_type.get_gz(gzg)
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1.0
        gzg.gz = gz

    @classmethod
    def poll(cls, context) -> bool: return gzg.gz.get_data(context)._poll(context) if hasattr(gzg.gz.get_data(context), 'poll') else False
    def invoke_prepare(gzg, context, gz) -> None: gzg.gz.get_data(context)._invoke_prepare(context)
    def draw_prepare(gzg, context): gzg.gz.get_data(context)._draw_prepare(context)
    def refresh(gzg, context): gzg.gz.get_data(context)._refresh(context)
