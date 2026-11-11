"""Token + tham số bootstrap từ HTML www.facebook.com (1 GET HTTPS duy nhất).

Mọi giá trị request cần: fb_dtsg, lsd, __user, __rev/__spin_t, __hsi, __ccg,
__hs, __dyn, __csr, __s. Thiếu cái nào → fallback hằng số build (FB chấp nhận
giá trị cũ, quan trọng nhất là fb_dtsg + lsd + __user).

jazoest = int("2" + str(sum(ord(c) for c in fb_dtsg))) — xác minh trên nhiều
cặp dtsg/jazoest bóc từ traffic web thật.
"""
import random
import re
import string
import time

from .spec import json_compact

# fallback tĩnh theo build của FB (giá trị công khai, client web ai cũng gửi)
_FALLBACK = {
    "__hs": "20768.HYP:comet_pkg.2.1...0",
    "__ccg": "EXCELLENT",
    "__spin_b": "trunk",
    "__comet_req": "15",
    "__aaid": "0",
    "__a": "1",
    "dpr": "1",
    "server_timestamps": "true",
}

_DTSG_PATTERNS = (
    r'\["DTSGInitialData",\[\],\{"token":"([^"]+)"',
    r'\["DTSGInitData",\[\],\{"token":"([^"]+)"',
    r'"DTSGInitData":\{"token":"([^"]+)"',
    r'\\"DTSGInitData\\",\[\],\{\\"token\\":\\"([^"\\]+)',
    r'\\"DTSGInitData\\":\{\\"token\\":\\"([^"\\]+)',
    r'name="fb_dtsg" value="([^"]+)"',
)
_LSD_PATTERNS = (
    r'\["LSD",\[\],\{"token":"([^"]+)"',
    r'"LSD",\[\],\{"token":"([^"]+)"',
    r'"LSD":\{"token":"([^"]+)"',
    r'\\"LSD\\",\[\],\{\\"token\\":\\"([^"\\]+)',
    r'\\"LSD\\":\{\\"token\\":\\"([^"\\]+)',
    r'name="lsd" value="([^"]+)"',
)


def jazoest(dtsg: str) -> str:
    return int("2" + str(sum(ord(c) for c in dtsg)))


def _find(patterns: tuple, html: str) -> str | None:
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)
    return None


def _rand_s() -> str:
    """__s — session tracking 3 nhóm 6 ký tự lowercase."""
    groups = ("".join(random.choices(string.ascii_lowercase + string.digits,
                                     k=6)) for _ in range(3))
    return ":".join(groups)


def _attr(html: str, key: str, n_digits: bool = True) -> str | None:
    for pat in (rf'"{key}":(\d+)', rf'"{key}":"([^"]+)"',
                rf'"{key}\\":\\"?([^"\\,]+)'):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def parse_bootstrap(html: str) -> dict:
    """Trích toàn bộ tham số cần cho GraphQL từ 1 trang HTML."""
    dtsg = _find(_DTSG_PATTERNS, html)
    lsd = _find(_LSD_PATTERNS, html)
    out = {
        "fb_dtsg": dtsg,
        "lsd": lsd,
        "__rev": _attr(html, "client_revision") or _attr(html, "__spin_r"),
        "__spin_t": _attr(html, "__spin_t"),
        "__hsi": _attr(html, "__hsi"),
        "__ccg": _find((r'"ccg":"([A-Z]+)"', r'"__ccg":"([A-Z]+)"'), html),
        "__hs": _find((r'"__hs":"([^"]+)"', r'"__hs\\":\\"([^"\\]+)'), html),
        "__dyn": _find((r'"__dyn":"([^"]+)"', r'"__dyn\\":\\"([^"\\]+)'), html),
        "__csr": _find((r'"__csr":"([^"]+)"', r'"__csr\\":\\"([^"\\]+)'), html),
        "spin_b": "trunk",
    }
    out["jazoest"] = jazoest(dtsg) if dtsg else None
    return out


class Params:
    """Bộ tham số request GraphQL/upload; refresh bằng GET home 1 lần/30 phút."""

    def __init__(self) -> None:
        self.dtsg: str | None = None
        self.lsd: str | None = None
        self.rev = "1054041874"
        self.spin_t = str(int(time.time()))
        self.hsi = "0"  # haste session id — server không bắt buộc
        self.ccg = "EXCELLENT"
        self.hs = _FALLBACK["__hs"]
        self.dyn = ""
        self.csr = ""
        self.req = 0  # counter __req (base36)

    # -------------------------------------------------------------- update
    def apply_bootstrap(self, html: str) -> None:
        b = parse_bootstrap(html)
        if b.get("fb_dtsg"):
            self.dtsg = b["fb_dtsg"]
        if b.get("lsd"):
            self.lsd = b["lsd"]
        if b.get("__rev"):
            self.rev = b["__rev"]
        if b.get("__spin_t"):
            self.spin_t = b["__spin_t"]
        if b.get("__hsi"):
            self.hsi = b["__hsi"]
        if b.get("__ccg"):
            self.ccg = b["__ccg"]
        if b.get("__hs"):
            self.hs = b["__hs"]
        self.dyn = b.get("__dyn") or self.dyn
        self.csr = b.get("__csr") or self.csr

    # ------------------------------------------------------------- builders
    def next_req(self) -> str:
        self.req = (self.req + 1) % (36 ** 3)
        alphabet = string.digits + string.ascii_lowercase
        n = self.req
        out = ""
        while n:
            out = alphabet[n % 36] + out
            n //= 36
        return out or "0"

    def base(self, user_id: str, crn: str) -> dict:
        """Tham số dùng chung query string (upload) và form body (graphql)."""
        p = {
            "av": user_id,
            "__aaid": _FALLBACK["__aaid"],
            "__user": user_id,
            "__a": _FALLBACK["__a"],
            "__req": self.next_req(),
            "__hs": self.hs,
            "dpr": _FALLBACK["dpr"],
            "__ccg": self.ccg,
            "__rev": self.rev,
            "__s": _rand_s(),
            "__hsi": self.hsi,
            "__spin_r": self.rev,
            "__spin_b": _FALLBACK["__spin_b"],
            "__spin_t": self.spin_t,
            "__crn": crn,
        }
        if self.dyn:
            p["__dyn"] = self.dyn
        if self.csr:
            p["__csr"] = self.csr
        if self.dtsg:
            p["fb_dtsg"] = self.dtsg
            p["jazoest"] = str(jazoest(self.dtsg))
        if self.lsd:
            p["lsd"] = self.lsd
        return p

    def graphql_extra(self, user_id: str, friendly: str) -> dict:
        return {
            "__comet_req": _FALLBACK["__comet_req"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": friendly,
            "server_timestamps": _FALLBACK["server_timestamps"],
        }


def attribution_chain() -> str:
    """navigation_data.attribution_id_v2 — dạng client web, timestamp mới."""
    now = int(time.time() * 1000)
    sub = random.randint(100000, 999999)
    trace = random.randint(1_000_000_00, 5_000_000_00) * 10
    return (f"CometHomeRoot.react,comet.home,via_cold_start,{now},"
            f"{sub},{trace},,")


def body_urlencoded(params: dict) -> str:
    """Form-encode với đúng thứ tự khoá (FB không đòi thứ tự nhưng giữ gần
    định dạng web client cho an toàn)."""
    from urllib.parse import quote
    parts = []
    for k, v in params.items():
        sv = v if isinstance(v, str) else json_compact(v)
        parts.append(f"{k}={quote(sv, safe='')}")
    return "&".join(parts)
