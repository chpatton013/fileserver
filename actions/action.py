class UnimplementedMethodError(TypeError):
    pass


class Action(object):
    def do(self, *args, **kwargs):
        raise UnimplementedMethodError()
