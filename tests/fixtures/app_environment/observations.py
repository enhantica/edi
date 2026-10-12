"""Prepare real app observations only for the host requested by a gate."""

from collections import UserDict


class Observations(UserDict):
    def __init__(self, observe):
        super().__init__()
        self.observe = observe

    def __missing__(self, key):
        value = self.observe(key)
        self[key] = value
        return value
