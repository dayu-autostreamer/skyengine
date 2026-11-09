"""Shared run ownership errors, independent of decisions and scenes."""


class RunReplaced(RuntimeError):
    """An operation belongs to a run that has been reset or closed."""
