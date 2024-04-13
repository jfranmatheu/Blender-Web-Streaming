from ctypes import Structure, c_float


class rctf(Structure):
    _fields_ = [
        ('xmin', c_float),
        ('xmax', c_float),
        ('ymin', c_float),
        ('ymax', c_float)
    ]

    @classmethod
    def get(cls, data) -> 'rctf':
        return cls.from_address(data.as_pointer())

''' /** float rectangle. */
typedef struct rctf {
  float xmin, xmax;
  float ymin, ymax;
} rctf; '''
