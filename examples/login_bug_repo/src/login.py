"""Deliberately buggy login implementation for the SafetyBox demo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    username: str
    password: str


USERS = {"alice": User("alice", "correct horse battery staple")}


def authenticate(username: str, password: str) -> bool:
    record = USERS.get(username)
    if record is None:
        return False
    # Bug: identity comparison rejects an equal password held by another string object.
    return record.password is password
