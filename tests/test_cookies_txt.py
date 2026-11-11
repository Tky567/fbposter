"""Test loader cookies.txt (Netscape format) — offline."""
from pathlib import Path

import pytest

from fbposter import FBClient, FBError

from .conftest import FakeHTTP

NETSCAPE = "\n".join([
    "# Netscape HTTP Cookie File",
    "# This is a generated file! Do not edit.",
    "",
    ".facebook.com\tTRUE\t/\tTRUE\t1999999999\tc_user\t100000000000001",
    ".facebook.com\tTRUE\t/\tTRUE\t1999999999\txs\tSYNTHETIC_XS_FROM_EXTENSION",
    ".facebook.com\tTRUE\t/\tTRUE\t1999999999\tdatr\tdatr25value",
    "# HttpOnly_.facebook.com\tTRUE\t/\tTRUE\t1999999999\txs\tSYNTHETIC_XS_HTTSONLY",
    ".example.com\tTRUE\t/\tTRUE\t1999999999\tc_user\t9999",
    ".discord.com\tTRUE\t/\tTRUE\t1999999999\tc_user\t8888",
    "bad-line-no-tabs",
    "",
])


def test_from_cookies_txt(tmp_path: Path):
    p = tmp_path / "cookies.txt"
    p.write_text(NETSCAPE, encoding="utf-8")
    fb = FBClient.from_cookies_txt(p)
    assert fb.user_id == "100000000000001"
    assert fb.cookies["xs"] == "SYNTHETIC_XS_HTTSONLY"  # HttpOnly thắng
    assert fb.cookies["datr"] == "datr25value"
    # cookie của domain khác không lọt vào
    assert "9999" not in str(fb.cookies)


def test_from_cookies_txt_missing_file(tmp_path: Path):
    with pytest.raises(FBError, match="không đọc được"):
        FBClient.from_cookies_txt(tmp_path / "nope.txt")


def test_from_cookies_txt_no_facebook(tmp_path: Path):
    p = tmp_path / "only_other.txt"
    p.write_text(".example.com\tTRUE\t/\tTRUE\t1999999999\ta\t1\n",
                 encoding="utf-8")
    with pytest.raises(FBError, match="không có cookie facebook"):
        FBClient.from_cookies_txt(p)


def test_from_cookies_txt_works_with_transport(tmp_path: Path):
    p = tmp_path / "cookies.txt"
    p.write_text(NETSCAPE, encoding="utf-8")
    fake = FakeHTTP()
    fb = FBClient.from_cookies_txt(p)
    fb.http = fake
    info = fb.verify()
    assert info["ok"] and info["user_id"] == "100000000000001"
