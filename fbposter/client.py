"""FBClient — thư viện đăng bài + quản lí bài đăng Facebook, thuần HTTPS.

Không browser, không playwright: chỉ curl_cffi (TLS fingerprint Chrome) gọi
facebook.com. Session = cookie c_user/xs (cookies.txt hoặc file JSON).

API:
    fb = FBClient.from_session_dir("sessions")
    fb = FBClient.from_cookies_txt("cookies.txt")   # Netscape format
    fb.verify()                      → thông tin session
    fb.create_post(text, images, audience) → {post_id, story_id, permalink,...}
    fb.list_posts(limit)             → [{post_id, text, time, permalink, story_id}]
    fb.edit_post(post_id, text, audience)
    fb.delete_post(post_id)
"""
from __future__ import annotations

import json
import random
import re
import string
import time
from pathlib import Path

from curl_cffi import requests as creq

from . import spec
from .tokens import Params, attribution_chain, body_urlencoded

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_SEC_CH_UA = '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"'

_BASE_HEADERS = {
    "user-agent": _UA,
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": _SEC_CH_UA,
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

_TOKEN_TTL = 30 * 60      # fb_dtsg sống ~vài giờ; refresh 30 phút
_REQUIRED_COOKIES = ("c_user", "xs")
_MAX_IMAGES = 4
_MAX_IMAGE_BYTES = 8 * 1024 * 1024
# FB thật nhận ≥5.05MB (test live 2026-11-11, 7680x4320 JPEG) — cap 8MB là
# kiểm tra hợp lý phía client, server là chốt cuối.

_MIME_BY_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
)


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """(mime, ext) từ magic bytes; None nếu không phải ảnh."""
    for magic, mime, ext in _MIME_BY_MAGIC:
        if data.startswith(magic):
            return mime, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def build_multipart(parts: list) -> tuple[bytes, str]:
    """Dựng multipart/form-data đúng dạng web client: text field không
    Content-Type; file part có filename + Content-Type."""
    boundary = ("----WebKitFormBoundary"
                + "".join(random.choices(string.ascii_letters + string.digits,
                                         k=16)))
    out = bytearray()
    for name, value in parts:
        out += f"--{boundary}\r\n".encode()
        if isinstance(value, tuple):
            filename, data, mime = value
            filename = (filename.replace('"', "%22")
                        .replace("\r", "").replace("\n", ""))
            out += (f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                    f"Content-Type: {mime}\r\n\r\n").encode()
            out += data
            out += b"\r\n"
        else:
            out += (f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n").encode()
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), boundary


def _dig(obj, *keys):
    """obj[k1][k2]... — None nếu thiếu khoá hoặc gặp null giữa chừng."""
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


class FBError(RuntimeError):
    """Lỗi Facebook có mã — message server + code khi có."""

    def __init__(self, message: str, code: int | None = None,
                 subcode: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode


# root trong data.* mà mỗi mutation trả về (để chọn đúng doc khi response
# ghép nhiều JSON)
_RESULT_ROOT = {
    "ComposerStoryCreateMutation": "story_create",
    "ComposerStoryEditMutation": "story_edit",
    "useCometFeedStoryDeleteMutation": "story_delete",
    "ProfileCometTimelineFeedRefetchQuery": "node",
    "CometPrivacySelectorEditableQuery": "node",
}


class FBClient:
    """Một phiên Facebook (cookie set) — dùng 1 instance/luồng."""

    def __init__(self, cookies: dict | list, http: creq.Session | None = None,
                 impersonate: str = "chrome") -> None:
        if isinstance(cookies, list):
            picked: dict = {}
            for c in cookies:
                name = c.get("name")
                if name and "value" in c and name not in picked:
                    picked[name] = c["value"]
            cookies = picked
        missing = [k for k in _REQUIRED_COOKIES if not cookies.get(k)]
        if missing:
            raise FBError(f"thiếu cookie {', '.join(missing)} — lấy lại cookie")
        self.cookies = dict(cookies)
        self.user_id = str(self.cookies["c_user"])
        self.http = http or creq.Session(impersonate=impersonate)
        self.http.headers.update(_BASE_HEADERS)
        self._set_cookies()
        self.params = Params()
        self._tokens_at = 0.0
        self._entry_nonce = "".join(
            random.choices(string.ascii_letters + string.digits, k=8))
        self._mutation_seq = 0
        self._actor_name: str | None = None

    # ------------------------------------------------------------ session
    @classmethod
    def from_session_dir(cls, directory: str | Path) -> FBClient:
        folder = Path(directory)
        files = (sorted(folder.glob("facebook_*.json"), reverse=True)
                 or sorted(folder.glob("*.json"), reverse=True))
        if not files:
            raise FBError(
                f"không có session facebook trong {directory} — cung cấp cookie")
        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise FBError(f"session file hỏng ({files[0].name}): {e}") from e
        cookies = data.get("cookies") if isinstance(data, dict) else data
        if not isinstance(cookies, (list, dict)):
            raise FBError(f"session file sai định dạng ({files[0].name}): cần "
                          'list cookie hoặc {"cookies": [...]}')
        return cls(cookies)

    @classmethod
    def from_cookies_txt(cls, path: str | Path) -> FBClient:
        """Đọc file cookies.txt định dạng Netscape (tiện ích
        Get cookies.txt LOCALLY, EditThisCookie...).

        Chỉ lấy cookie *.facebook.com; dòng `# HttpOnly_` vẫn là cookie
        thật — bỏ prefix, đọc tiếp. Trùng name → bản sau (HttpOnly) thắng.
        """
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except OSError as e:
            raise FBError(f"không đọc được {path}: {e}") from e
        picked: list[dict] = []
        index: dict[str, int] = {}
        for line in text.splitlines():
            body = line.strip()
            if body.startswith("# HttpOnly_"):
                body = body[len("# HttpOnly_"):]
            if not body or body.startswith("#"):
                continue
            parts = body.split("\t")
            if len(parts) < 7:
                continue
            domain, _flag, _path, _secure, _expires, name, value = parts[:7]
            # khớp chặt: evilfacebook.com / facebook.com.attacker.io phải loại
            domain = domain.lstrip(".").lower()
            if (domain != "facebook.com"
                    and not domain.endswith(".facebook.com")):
                continue
            if not name or value == "":
                continue
            cookie = {"domain": domain, "name": name, "path": _path,
                      "secure": _secure.upper() == "TRUE", "value": value}
            if name in index:
                picked[index[name]] = cookie
            else:
                index[name] = len(picked)
                picked.append(cookie)
        if not picked:
            raise FBError(f"{path} không có cookie facebook.com nào")
        return cls(picked)

    def _set_cookies(self) -> None:
        for name, value in self.cookies.items():
            self.http.cookies.set(name, value, domain=".facebook.com", path="/")

    # ------------------------------------------------------------ low level
    def _ensure_tokens(self, force: bool = False) -> None:
        if not force and self.params.dtsg and (
                time.time() - self._tokens_at < _TOKEN_TTL):
            return
        r = self._get(spec.HOME_URL)
        if not r.ok:
            raise FBError(f"facebook.com trả {r.status_code}")
        html = r.text
        if ("DTSGInitData" not in html and "fb_dtsg" not in html
                and ("/login" in str(r.url) or 'name="login"' in html)):
            raise FBError(
                "session facebook hết hạn hoặc checkpoint — lấy lại cookie")
        self.params.apply_bootstrap(html)
        self._tokens_at = time.time()
        if not self._actor_name:
            m = re.search(r'"name":"([^"]{1,80})","short_name"', html)
            if m:
                self._actor_name = m.group(1)
        # đối chiếu user trong HTML với cookie c_user — session sai/kéo
        # cookie từ tài khoản khác là phát hiện ngay (pattern live-verified)
        m = re.search(r'"USER_ID":"(\d+)"', html)
        if m and m.group(1) != self.user_id:
            raise FBError(
                f"cookie không khớp tài khoản đang đăng nhập "
                f"(HTML USER_ID={m.group(1)} ≠ c_user={self.user_id})")
        if not self.params.dtsg:
            raise FBError("không bóc được fb_dtsg từ home — session có thể "
                          "bị hạn chế, lấy lại cookie")

    def _get(self, url: str, **kw) -> creq.Response:
        kw.setdefault("timeout", 60)
        kw.setdefault("allow_redirects", True)
        return self.http.get(url, **kw)

    def _next_mutation_id(self) -> str:
        self._mutation_seq += 1
        return str(self._mutation_seq)

    def _graphql(self, friendly: str, doc_id: str, variables: dict,
                 crn: str) -> dict:
        self._ensure_tokens()
        body = self.params.base(self.user_id, crn)
        body.update(self.params.graphql_extra(self.user_id, friendly))
        body["variables"] = spec.json_compact(variables)
        body["doc_id"] = doc_id
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "x-fb-friendly-name": friendly,
            "x-fb-lsd": self.params.lsd or "",
            "x-fb-entry-nonce": self._entry_nonce,
            "accept": "*/*",
            "priority": "u=1, i",
        }
        r = self.http.post(spec.GRAPHQL_URL,
                           data=body_urlencoded(body).encode("utf-8"),
                           headers=headers, timeout=60)
        if r.status_code == 404:
            raise FBError(f"doc_id {doc_id} đã cũ ({friendly}) — chụp lại "
                          "mutation từ web rồi sửa fbposter/spec.py")
        if r.status_code == 429:
            raise FBError("facebook giới hạn tốc độ (429) — chờ rồi thử lại",
                          429)
        if r.status_code >= 500:
            raise FBError(f"facebook lỗi máy chủ ({r.status_code}) — thử lại "
                          "sau", r.status_code)
        docs = self._parse_docs(r)
        want = _RESULT_ROOT.get(friendly)
        chosen = None
        first_err = None
        for doc in docs:
            data = doc.get("data")
            usable = isinstance(data, dict) and (
                data.get(want) is not None if want else bool(data))
            if usable:  # lỗi từng phần đi kèm data hợp lệ không phải thất bại
                chosen = doc
                break
            if first_err is None and (doc.get("errors") or doc.get("error")):
                first_err = doc
        if chosen is None:
            if first_err is not None:
                if first_err.get("errors"):
                    self._raise_graphql_errors(first_err, friendly)
                legacy = self._legacy_error(first_err)
                if legacy:
                    raise legacy
            chosen = docs[0]
        return chosen or {}

    @staticmethod
    def _legacy_error(doc: dict) -> FBError | None:
        """Lỗi dạng {"error": 1357001, "errorSummary": "..."} (HTTP 200)."""
        if not isinstance(doc, dict) or not doc.get("error"):
            return None
        msg = doc.get("errorSummary") or doc.get("errorDescription")
        if not msg:
            return None
        code = doc["error"] if isinstance(doc["error"], int) else None
        if code in (1357001, 1357004) or "login" in str(msg).lower():
            return FBError(f"session facebook chết ({msg}) — lấy lại cookie", code)
        return FBError(f"facebook từ chối: {msg}", code)

    @staticmethod
    def _parse_docs(r: creq.Response) -> list:
        """Response GraphQL có thể ghép nhiều JSON (`{..}{..}` preloader
        batch) — tách ra giữ thứ tự."""
        text = r.text
        m = re.match(r"for\s*\(\s*;\s*;\s*\);", text)
        if m:
            text = text[m.end():]
        docs = []
        dec = json.JSONDecoder()
        pos = 0
        while pos < len(text):
            s = text.find("{", pos)
            if s < 0:
                break
            try:
                obj, end = dec.raw_decode(text, s)
            except json.JSONDecodeError:
                pos = s + 1
                continue
            docs.append(obj)
            pos = end
        if not docs:
            raise FBError("facebook trả response rỗng/không parse được")
        return docs

    @staticmethod
    def _raise_graphql_errors(data: dict, friendly: str) -> None:
        errs = data.get("errors") if isinstance(data, dict) else None
        if not errs:
            return
        e0 = errs[0] if isinstance(errs, list) else errs
        msg = str(e0.get("message") or e0.get("summary") or "unknown")
        code = e0.get("code") or e0.get("error") or None
        subcode = e0.get("subcode") or e0.get("error_subcode") or None
        low = msg.lower()
        if "login" in low or code in (1357001, 1357004):
            raise FBError(f"session facebook chết ({msg}) — lấy lại cookie", code,
                          subcode)
        raise FBError(f"facebook từ chối {friendly}: {msg}", code, subcode)

    # ------------------------------------------------------------- verify
    def verify(self) -> dict:
        self._ensure_tokens(force=True)
        return {
            "ok": True,
            "user_id": self.user_id,
            "name": self._actor_name,
            "dtsg_len": len(self.params.dtsg or ""),
            "rev": self.params.rev,
        }

    # ------------------------------------------------------- photo upload
    def upload_photo(self, data: bytes | str | Path, filename: str = "") -> str:
        """Upload 1 ảnh (bytes hoặc đường dẫn file) → photo_id."""
        if isinstance(data, (str, Path)):
            path = Path(data)
            if not path.is_file():
                raise FBError(f"file ảnh không tồn tại: {path}")
            filename = filename or path.name
            data = path.read_bytes()
        if len(data) > _MAX_IMAGE_BYTES:
            raise FBError(f"ảnh vượt {_MAX_IMAGE_BYTES // (1024 * 1024)}MB "
                          f"({len(data) // 1024}KB)")
        sniffed = sniff_image(data)
        if not sniffed:
            raise FBError("ảnh không hợp lệ (cần JPEG/PNG/GIF/WEBP)")
        mime, ext = sniffed
        if not filename:
            filename = f"photo{ext}"
        elif "." not in filename:
            filename = f"{filename}{ext}"
        self._ensure_tokens()
        params = self.params.base(self.user_id, spec.CRN["upload"])
        parts = [("source", "8"),
                 ("profile_id", self.user_id),
                 ("waterfallxapp", "comet"),
                 ("farr", (filename, data, mime))]
        headers = {
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "accept": "*/*",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        }
        r = self._post_upload(spec.UPLOAD_URL, params, parts, headers)
        if r.status_code != 200:
            raise FBError(f"upload ảnh trả {r.status_code}")
        payload = {}
        docs = self._parse_docs(r)
        for doc in docs:
            if isinstance(doc.get("payload"), dict) and doc["payload"]:
                payload = doc["payload"]
                break
        pid = payload.get("photoID")
        if not pid:
            for doc in docs:
                legacy = self._legacy_error(doc)
                if legacy:
                    raise legacy
            raise FBError("upload ảnh thành công nhưng không có photoID")
        return str(pid)

    def _post_upload(self, url: str, params: dict, parts: list,
                     headers: dict) -> creq.Response:
        """Multipart POST — body tự dựng (curl_cffi files= không hỗ trợ ở
        0.17, CurlMime bị endpoint trả payload rỗng)."""
        body, boundary = build_multipart(parts)
        headers = dict(headers)
        headers["content-type"] = f"multipart/form-data; boundary={boundary}"
        return self.http.post(url, params=params, data=body,
                              headers=headers, timeout=120)

    # ------------------------------------------------------- create post
    def create_post(self, text: str,
                    images: list[bytes | str | Path] | None = None,
                    audience: str | None = "public",
                    ai_generated: bool = False,
                    photo_ids: list[str] | None = None) -> dict:
        """Đăng bài lên profile cá nhân. Trả {post_id, story_id, permalink}.

        audience: public | friends | only_me | None (giữ default tài khoản).
        ai_generated: bật nhãn "AI generated" của composer.
        photo_ids: photoID đã upload sẵn (upload_photo) — gắn trực tiếp,
        không upload lại. Tối đa 4 ảnh/bài (uploaded + photo_ids) — vượt raise."""
        self._check_audience(audience)
        if isinstance(images, (str, bytes, Path)):
            images = [images]
        body = text.strip()
        if not body and not images and not photo_ids:
            raise FBError("bài trống: cần text hoặc ảnh")
        attached = [str(p) for p in (photo_ids or [])]
        if len(attached) + len(images or []) > _MAX_IMAGES:
            raise FBError(f"tối đa {_MAX_IMAGES} ảnh/bài — nhận "
                          f"{len(attached) + len(images or [])}")
        uploaded: list[str] = []
        for item in images or []:
            uploaded.append(self._upload_from(item))
        session_id = spec.new_session_id()
        variables = spec.create_variables(
            body, self.user_id, attached + uploaded or None, audience,
            session_id, self._next_mutation_id(), attribution_chain(),
            ai_generated=ai_generated)
        data = self._graphql("ComposerStoryCreateMutation", spec.DOC_CREATE,
                             variables, spec.CRN["create"])
        story = _dig(data, "data", "story_create", "story") or {}
        post_id = story.get("legacy_story_hideable_id") or ""
        if not post_id:
            # publishing_flow FALLBACK vẫn có story; thiếu hẳn → lỗi thật
            raise FBError("facebook không trả post_id — bài có thể chưa lên "
                          f"(publishing_flow={_dig(data, 'data', 'story_create', 'publishing_flow')})")
        return {
            "post_id": str(post_id),
            "story_id": story.get("id") or "",
            "permalink": story.get("url") or None,
            "photo_ids": attached + uploaded,
            "session_id": session_id,
        }

    @staticmethod
    def _check_audience(audience: str | None) -> None:
        if audience is not None and audience not in spec.PRIVACY_BASE_STATE:
            raise FBError(f"audience không hợp lệ: {audience} "
                          "(public | friends | only_me)")

    def _upload_from(self, item: bytes | str | Path) -> str:
        return self.upload_photo(item)

    # ---------------------------------------------------------- list posts
    def list_posts(self, limit: int = 10) -> list[dict]:
        """Bài viết trên profile cá nhân (mới nhất trước), phân trang bằng
        cursor của edge."""
        out: list[dict] = []
        cursor: str | None = None
        sent: set = set()
        seen_ids: set[str] = set()
        self._ensure_tokens()
        while len(out) < limit:
            if cursor in sent:
                break
            sent.add(cursor)
            count = min(max(limit - len(out), 1), 30)
            variables = spec.timeline_variables(self.user_id, count, cursor)
            data = self._graphql("ProfileCometTimelineFeedRefetchQuery",
                                 spec.DOC_TIMELINE, variables,
                                 spec.CRN["timeline"])
            node = _dig(data, "data", "node") or {}
            units = node.get("timeline_list_feed_units") or {}
            edges = units.get("edges") or []
            if not edges:
                break
            last_cursor = cursor
            for edge in edges:
                if len(out) >= limit:
                    break
                post = self._edge_post(edge)
                if post and post["post_id"] not in seen_ids:
                    seen_ids.add(post["post_id"])
                    out.append(post)
                cur = (edge.get("cursor")
                       or (edge.get("node") or {}).get("cursor"))
                if cur:
                    cursor = cur
            page_info = units.get("page_info") or {}
            if page_info.get("end_cursor"):
                cursor = page_info["end_cursor"]
            if not cursor or cursor == last_cursor or len(out) >= limit:
                break
        return out

    @staticmethod
    def _edge_post(edge: dict) -> dict | None:
        if not isinstance(edge, dict):
            return None
        node = edge.get("node") or {}
        post_id = node.get("post_id") or ""
        if not post_id:
            story = node.get("story") or {}
            post_id = story.get("post_id") or ""
        if not post_id:
            return None
        text = node.get("message") if isinstance(node.get("message"), dict) \
            else None
        text = text or (node.get("story") or {}).get("message")
        if isinstance(text, dict):
            text = text.get("text")
        text = text or ""
        sections = (node.get("comet_sections") or {})
        content = (sections.get("content") or {})
        content_story = (content.get("story") or {})
        if not text:
            msg = content_story.get("message")
            text = msg.get("text") if isinstance(msg, dict) else ""
        permalink = (node.get("permalink_url") or content_story.get("url")
                     or "")
        if permalink and permalink.startswith("/"):
            permalink = "https://www.facebook.com" + permalink
        return {
            "post_id": str(post_id),
            "story_id": node.get("id") or (content_story.get("id") or ""),
            "text": str(text or ""),
            "time": node.get("creation_time") or content_story.get("creation_time"),
            "permalink": permalink or None,
        }

    # ----------------------------------------------------------- edit post
    def edit_post(self, post_id: str, text: str | None = None,
                  audience: str | None = None,
                  ai_generated: bool | None = None) -> dict:
        """Sửa bài đã đăng (text và/hoặc đối tượng và/hoặc nhãn AI)."""
        if text is None and audience is None and ai_generated is None:
            raise FBError("edit_post: cần text hoặc audience hoặc ai_generated")
        self._check_audience(audience)
        story_id = spec.encode_story_id(self.user_id, str(post_id),
                                        long_form=True)
        session_id = spec.new_session_id()
        # không gửi audience → giữ nguyên; nhưng input đòi message.text đủ,
        # lấy text cũ nếu chỉ đổi audience
        new_text = text
        if new_text is None:
            new_text = self._find_post_text(post_id)
            if new_text is None:
                # gửi "" sẽ xoá sạch nội dung bài → dừng thay vì đoán
                raise FBError(
                    f"không đọc được nội dung hiện tại của bài {post_id} "
                    "(bài cũ/đã ghim?) — truyền text=... để sửa an toàn")
        variables = spec.edit_variables(new_text, story_id, self.user_id,
                                        audience, session_id,
                                        self._next_mutation_id(),
                                        ai_generated=ai_generated)
        data = self._graphql("ComposerStoryEditMutation", spec.DOC_EDIT,
                             variables, spec.CRN["edit"])
        story = _dig(data, "data", "story_edit", "story") or {}
        return {
            "post_id": str(post_id),
            "story_id": story_id,
            "text": ((story.get("message") or {}).get("text")
                     if isinstance(story.get("message"), dict) else None)
            or new_text,
            "session_id": session_id,
        }

    def _find_post_text(self, post_id: str) -> str | None:
        for post in self.list_posts(limit=50):
            if post["post_id"] == str(post_id):
                return post["text"]
        return None

    # --------------------------------------------------------- delete post
    def delete_post(self, post_id: str) -> bool:
        story_id = spec.encode_story_id(self.user_id, str(post_id),
                                        long_form=True)
        variables = spec.delete_variables(story_id, self.user_id,
                                          self._next_mutation_id())
        data = self._graphql("useCometFeedStoryDeleteMutation", spec.DOC_DELETE,
                             variables, spec.CRN["delete"])
        deleted = _dig(data, "data", "story_delete", "deleted_story_id")
        if not deleted:
            raise FBError("facebook không xác nhận xoá bài")
        return True

    # ------------------------------------------------------- read privacy
    def get_post_privacy(self, post_id: str) -> str | None:
        """Đọc base_state hiện tại của bài (EVERYONE/FRIENDS/SELF...)."""
        variables = spec.privacy_query_variables(str(post_id))
        data = self._graphql("CometPrivacySelectorEditableQuery",
                             spec.DOC_PRIVACY, variables,
                             spec.CRN["edit"])
        node = _dig(data, "data", "node") or {}
        row = node.get("privacy_row_input") or {}
        base = row.get("base_state")
        if not base:
            scope = node.get("scope") or {}
            selected = scope.get("selected_option") or {}
            base = (selected.get("privacy_row_input") or {}).get("base_state")
        return base

    # ------------------------------------------------------------- close
    def close(self) -> None:
        try:
            self.http.close()
        except Exception:  # noqa: S110, BLE001 — close là phụ
            pass

    def __enter__(self) -> FBClient:  # noqa: PYI034 — Self chỉ có từ 3.11
        return self

    def __exit__(self, *exc) -> None:
        self.close()
