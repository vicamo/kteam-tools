#
# Class to hold pointers to all our shared datasets and long term connections.
# These are initially unbound early initialisation needs to bind appropriate
# values to them.  If a callable is bound, then that will be called on first
# use and the result will become its value.
#
# Existing attributes: lp -- direct launchpad connection.
#
class Context:

    __ready = False

    def __init__(self):
        self.__maker = {}
        self.__ready = True

    def __getattr__(self, name):
        if name not in self.__maker:
            raise AttributeError("{}: context has no such attribute".format(name))
        value = self.__maker[name]()
        super().__setattr__(name, value)
        return value

    def __setattr__(self, name, value):
        if self.__ready and hasattr(self, name):
            raise AttributeError("{}: read-only attribute".format(name))
        if callable(value):
            self.__maker[name] = value
        else:
            super().__setattr__(name, value)


ctx = Context()
