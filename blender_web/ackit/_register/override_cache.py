from collections import defaultdict


_cache_reset = {}
_mod_cls_attributes = defaultdict(set)


def get_attr_from_cache(cls, attr, default=None):
    if cls_cache := _cache_reset.get(cls, None):
        if hasattr(cls_cache, attr):
            return cls_cache[attr]
        else:
            print(f"No cache attr '{attr}' for cls '{cls}'")
    else:
        print(f"No cache for cls:", cls)
    return default

def cache_cls_attributes(cls) -> dict:
    _cache_reset[cls] = cls.__dict__.copy()
    return _cache_reset[cls]


def set_cls_attribute(cls, attr: str, new_value) -> callable:
    ## print("CLS ATTR:", cls, attr, getattr(cls, attr))

    if cache := _cache_reset.get(cls, None):
        pass
    else:
        cache = cache_cls_attributes(cls)

    setattr(cls, attr, new_value)

    if attr not in cache:
        print("Attribute %s not in cls" % attr, cls)
        return None

    _mod_cls_attributes[cls].add(attr)

    setattr(cls, 'old_' + attr, cache[attr])
    return cache[attr]


def unregister():
    for cls, mod_cls_attributes in _mod_cls_attributes.items():
        cache = _cache_reset[cls] # raises AttributeError on class without decorator
        for mod_attr in mod_cls_attributes:
            if not hasattr(cls, mod_attr) or mod_attr not in cache:
                # WTF! This should not happen...
                continue
            setattr(cls, mod_attr, cache[mod_attr])
            old_attr = 'old_' + mod_attr
            if not hasattr(cls, old_attr) or old_attr not in cache:
                continue
            delattr(cls, old_attr)
