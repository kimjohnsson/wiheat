"""Minimal stand-in for aiohttp (test use only). Only the names the API imports."""


class ClientError(Exception):
    pass


class ClientSession:
    pass
