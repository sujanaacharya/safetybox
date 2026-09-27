import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from login import authenticate  # noqa: E402


def test_login_accepts_equal_password_value() -> None:
    password = "".join(["correct horse", " battery staple"])
    assert authenticate("alice", password)


def test_login_rejects_wrong_password() -> None:
    assert not authenticate("alice", "wrong")
