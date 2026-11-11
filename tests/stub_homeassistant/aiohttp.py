"""Minimal stand-in for aiohttp (test use only). Only the names the API imports."""


class ClientError(Exception):
    pass


class ClientTimeout:
    def __init__(self, total=None, **kwargs):
        self.total = total


class ClientSession:
    pass
