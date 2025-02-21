"""A python module that extends the threading module to allow for the return of values from a thread"""

from threading import Thread
from typing import Any

class CustomThread(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)

        self.return_value = None

    def add_arg(self, arg: Any):
        """Adds an argument to the thread after definition.

        Args:
            arg (Any): The argument to add to the thread.
        """
        self._args += (arg,)

    def run(self):
        if self._target:
            self.return_value = self._target(*self._args, **self._kwargs)

    