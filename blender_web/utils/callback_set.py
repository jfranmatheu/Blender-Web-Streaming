


class CallbackSet(object):
    def __init__(self):
        self.id = id(self)
        self.callbacks = set()

    def connect(self, callback: callable):
        self += callback

    def disconnect(self, callback: callable):
        self -= callback

    def clear(self):
        self.callbacks.clear()

    def __iadd__(self, callback: callable):
        ''' Implements addition with assignment (+=). '''
        # print("* Added callback! -> ", callback)
        if not callback:
            return
        self.callbacks.add(callback)
        return self

    def __isub__(self, callback: callable):
        ''' Implements subtraction with assignment (-=). '''
        if isinstance(callback, int):
            if len(self) < callback:
                return
            self.callbacks.pop(callback)
        elif callback in self:
            self.callbacks.remove(callback)
        return self

    def __add__(self, callback: callable):
        raise NotImplementedError

    def __sub__(self, callback: callable):
        raise NotImplementedError

    def __le__(self, callback: callable):
        ''' Replaces the callbacks with a single callback,
            if it is None, it will just clear all callbacks. '''
        self.callbacks.clear()
        if callback:
            self += callback
        return self

    def __call__(self, *args, **kwargs):
        for call in self.callbacks: call(*args, **kwargs)# ; print("\t* Callback:", call)

    '''
    def __repr__(self):
        return self.callbacks

    def __str__(self):
        return str(self.callbacks)
    '''
