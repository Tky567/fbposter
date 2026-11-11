"""Transport giả — mọi test chạy offline, không gọi facebook.com."""
from urllib.parse import parse_qs

import pytest

from fbposter import FBClient
from fbposter.tokens import body_urlencoded

# Giá trị synthetic — không phải dữ liệu session thật của ai cả.
DTSG_A = "SYNTHETIC_DTSG_TOKEN_AAAA0001:46:1794370736"
DTSG_B = "SYNTHETIC_DTSG_TOKEN_BBBB0002:46:1794370736"
DTSG_C = "SYNTHETIC_DTSG_TOKEN_CCCC0003:46:1794370736"
LSD = "SYNTHETIC_LSD_TOKEN_000000"
HIS = 1234567890123456

ACTOR = "100000000000001"
POST = "1677000000000001"

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d4944415478da63f8cf000000030101002b0d0a2e"
)

FIXTURE_HTML = (
    "<html><script>\n"
    '{"DTSGInitData":{"token":"' + DTSG_A + '"},"LSD",[],'
    '{"token":"' + LSD + '"},\n'
    f'"client_revision":1054041874,"__hsi":{HIS},'
    '"__spin_t":1794373827}\n'
    "</script></html>\n"
)


class FakeResponse:
    def __init__(self, text, status_code=200, url="https://www.facebook.com/"):
        self.text = text
        self.status_code = status_code
        self.url = url

    @property
    def ok(self) -> bool:
        return self.status_code == 200


class FakeJar:
    def __init__(self):
        self.cookies = {}

    def set(self, name, value, domain=None, path=None):
        self.cookies[name] = value


class FakeHTTP:
    """Session giả — ghi lại mọi call, trả fixture theo friendly-name."""

    def __init__(self):
        self.headers = {}
        self.cookies = FakeJar()
        self.home_html = FIXTURE_HTML
        self.responses = {}
        self.upload_payload = '{"payload": {"photoID": "1677000000000009"}}'
        self.posts = []

    def get(self, url, **kw):
        return FakeResponse(self.home_html, url=url)

    def post(self, url, data=None, params=None, files=None, headers=None,
             **kw):
        form = {}
        if isinstance(data, (bytes, str)):
            form = {k: v[0] for k, v in parse_qs(
                data.decode() if isinstance(data, bytes) else data,
                keep_blank_values=True).items()}
        elif isinstance(data, dict):
            form = dict(data)
        self.posts.append({
            "url": url, "form": form, "params": params or {},
            "files": files or {}, "headers": headers or {},
        })
        if "upload.facebook.com" in url:
            return FakeResponse(self.upload_payload)
        friendly = form.get("fb_api_req_friendly_name", "")
        return FakeResponse(self.responses.get(friendly, "{}"))

    def close(self):
        pass


def decode_form(call: dict) -> str:
    data = call["form"]
    if isinstance(data, bytes):
        return data.decode()
    if isinstance(data, str):
        return data
    return body_urlencoded(data)


@pytest.fixture()
def fake() -> FakeHTTP:
    return FakeHTTP()


@pytest.fixture()
def fb(fake: FakeHTTP) -> FBClient:
    return FBClient({"c_user": ACTOR, "xs": "SYNTHETIC_XS_VALUE", "datr": "d"},
                    http=fake)
