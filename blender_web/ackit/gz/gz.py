
class BWS_BaseGZ:
    data_type = None
    _data_instance = None
    _gz_instance = None
    use_singleton: bool

    @classmethod
    def get_data(cls, ctx):
        if cls._data_instance is None:
            cls._data_instance = cls.data_type(ctx)
        return cls._data_instance

    @classmethod
    def get_gz(cls, gzg):
        if cls.use_singleton:
            if cls._gz_instance is None:
                cls._gz_instance = gzg.gizmos.new(cls.bl_idname)
            return cls._gz_instance
        return gzg.gizmos.new(cls.bl_idname)

    def setup(gz): pass
    def test_select(gz,c,l): return 1 if gz.get_data(c)._test_select(c,l) else -1
    def invoke(gz,c,e): return gz.get_data(c)._invoke(c,e)
    def modal(gz,c,e,t): return gz.get_data(c)._modal(c,e,t)
    def exit(gz,c,ca): return gz.get_data(c)._exit(c,ca)
    def draw(gz,c): gz.get_data(c)._draw(c)
