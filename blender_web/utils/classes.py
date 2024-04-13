from typing import Type, List, Dict
from collections import defaultdict
import inspect


def get_subclasses_recursive(base_cls, only_outermost: bool = False):
    all_subclasses = []

    def iter_subclasses(cls):
        nonlocal all_subclasses
        subclasses = cls.__subclasses__()
        if only_outermost and len(subclasses) == 0:
            all_subclasses.append(cls)
        else:
            for subclass in subclasses:
                if not only_outermost:
                    all_subclasses.append(subclass)
                iter_subclasses(subclass)

    iter_subclasses(base_cls)
    return all_subclasses


def pack_classes_by_modules(classes: list, one_per_module: bool = False) -> Dict[str, List[Type]]:
    if one_per_module:
        return {cls.__module__.split('.')[-2]: cls for cls in classes}
    d = defaultdict(list)
    for cls in classes:
        d[cls.__module__.split('.')[-2]].append(cls)
    return d


def get_inner_classes_of_type(cls, inner_class_type):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)
            and issubclass(cls_attribute, inner_class_type)]

def get_inner_classes(cls):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)]
