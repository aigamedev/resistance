import collections


class Observable(type):
    """Helper meta-class that makes it possible to define observer functions
    in derived classes without having to explicitly call the base class.  The
    observers of the base classes are always called before those of the
    specialized classes.
    """
    def __new__(cls, name, parents, dct):
        __hooks__ = collections.defaultdict(list)
        if name != 'Bot':
            for (k, v) in dct.items():
                if not k.startswith('on'):
                    continue
                __hooks__[k].append(v)
                del dct[k]
            dct['__hooks__'] = __hooks__
        else:
            for (k, v) in dct.items():
                if not k.startswith('on'):
                    continue
                def bind(name=k, function=v):
                    def wrap(self, *args, **kwargs):
                        for c in reversed(self.__class__.__mro__):                            
                            if hasattr(c, '__hooks__'):
                                for m in c.__hooks__.get(name, []):
                                    m(self, *args, **kwargs)
                        return function(self, *args, **kwargs)
                    return wrap
                dct[k] = bind()
        return super(Observable, cls).__new__(cls, name, parents, dct)
