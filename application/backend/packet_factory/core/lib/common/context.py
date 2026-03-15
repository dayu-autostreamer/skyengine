import os

class Context:
    """The Context provides the capability of obtaining the context"""
    parameters = os.environ

    @classmethod
    def get_parameter(cls, param, default=None, direct=True):
        """get the value of the key `param` in `PARAMETERS`,
        if not exist, the default value is returned"""

        value = cls.parameters.get(param) or cls.parameters.get(str(param).upper())
        value = value if value else default

        if not direct:
            value = eval(value)

        return value