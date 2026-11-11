"""Test bootstrap token — offline."""
from fbposter.tokens import Params, attribution_chain, body_urlencoded, jazoest, parse_bootstrap

from .conftest import DTSG_A, DTSG_B, DTSG_C, FIXTURE_HTML, HIS, LSD


def test_jazoest_formula():
    # công thức jazoest = int("2" + str(sum(ord(c) for c in dtsg)))
    assert jazoest(DTSG_A) == 22877
    assert jazoest(DTSG_B) == 22882
    assert jazoest(DTSG_C) == 22887


def test_parse_bootstrap():
    b = parse_bootstrap(FIXTURE_HTML)
    assert b["fb_dtsg"] == DTSG_A
    assert b["lsd"] == LSD
    assert b["__rev"] == "1054041874"
    assert b["__hsi"] == str(HIS)
    assert b["jazoest"] == 22877


def test_parse_bootstrap_empty():
    b = parse_bootstrap("<html></html>")
    assert b["fb_dtsg"] is None
    assert b["lsd"] is None
    assert b["jazoest"] is None


def test_params_next_req_base36():
    p = Params()
    assert p.next_req() == "1"
    for _ in range(10):
        p.next_req()
    v = p.next_req()
    assert v == "c"  # 12 trong base36


def test_params_base_fields():
    p = Params()
    p.dtsg = DTSG_A
    p.lsd = LSD
    d = p.base("100", "COMET_HOME")
    assert d["av"] == "100"
    assert d["__user"] == "100"
    assert d["__crn"] == "COMET_HOME"
    assert d["fb_dtsg"] == DTSG_A
    assert d["jazoest"] == "22877"
    assert d["lsd"] == LSD
    assert "__s" in d and d["__s"].count(":") == 2


def test_attribution_chain_shape():
    a = attribution_chain()
    parts = a.split(",")
    assert parts[0] == "CometHomeRoot.react"
    assert parts[1] == "comet.home"
    assert parts[2] == "via_cold_start"
    assert parts[3].isdigit()
    assert a.endswith(",,")


def test_body_urlencoded():
    out = body_urlencoded({"a": "x y", "b": "1"})
    assert out == "a=x%20y&b=1"
