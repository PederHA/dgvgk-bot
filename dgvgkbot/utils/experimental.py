import inspect

from discord.ext import commands

from utils.exceptions import NoContextException


def get_ctx() -> commands.Context:
    """Attempts to retrieve discord context from the call stack."""
    frame = inspect.currentframe()
    while frame:
        _locals = dict(frame.f_locals)
        for k, v in _locals.items():
            if isinstance(v, commands.Context):
                return v
        else:
            frame = frame.f_back
    else:
        raise NoContextException("Cannot find context in call stack!")