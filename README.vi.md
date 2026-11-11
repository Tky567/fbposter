<div align="center">

# fbposter

**Thư viện Python không chính thức, không browser — đăng và quản lí bài trên
profile Facebook của chính bạn.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](#tr%E1%BA%A1ng-th%C3%A1i)
[![Unofficial](https://img.shields.io/badge/Meta-unofficial-red.svg)](#mi%E1%BB%85n-tr%E1%BB%AB)

[Tiếng Việt](README.vi.md) · English

</div>

> [!WARNING]
> **Thư viện không chính thức tự động hoá tài khoản Facebook cá nhân.** Không
> liên quan tới, không được Meta chứng thực. Tự động hoá có thể vi phạm điều
> khoản dịch vụ của Facebook và dẫn tới checkpoint, hạn chế hoặc khoá tài
> khoản. Chỉ dùng trên **tài khoản của chính bạn**, nhịp chậm, rủi ro tự chịu.

---

## Vì sao thư viện này tồn tại?

Graph API chính thức của Facebook không cho app bên thứ ba đăng lên timeline
**profile cá nhân**. Cách duy nhất là web composer. `fbposter` nói chuyện
trực tiếp với các endpoint GraphQL + upload nội bộ mà web client dùng, bằng
HTTPS thuần và TLS fingerprint Chrome (qua
[`curl_cffi`](https://github.com/lexiforest/curl_cffi)) — không Selenium, không
Playwright, không browser phải chạy.

Các endpoint này là private, **có thể đổi bất cứ lúc nào** khi Facebook deploy
mới.

## Cài đặt

```bash
pip install git+https://github.com/Tky567/fbposter.git
```

Chưa có trên PyPI. Yêu cầu Python ≥ 3.10, dependency duy nhất: `curl_cffi`.

## Lấy cookie

Cần cookie của phiên web Facebook đã đăng nhập: tối thiểu **`c_user`** và
**`xs`**, nên kèm `datr`.

> [!CAUTION]
> Cookie = toàn quyền tài khoản. Đừng dán vào issue/chat, đừng commit lên git.

**Cách A — file JSON** `sessions/facebook_main.json`:

```json
[
  {"name": "c_user", "value": "YOUR_USER_ID"},
  {"name": "xs",     "value": "YOUR_XS_COOKIE"},
  {"name": "datr",   "value": "YOUR_DATR_COOKIE"}
]
```

Dạng `{"cookies": [ ... ]}` cũng nhận.

**Cách B — `cookies.txt`** (Netscape format, tiện ích *Get cookies.txt
LOCALLY*...): nạp thẳng, chỉ đọc cookie `*.facebook.com`, khớp domain chặt.

Đăng xuất / đổi mật khẩu → cookie chết, export mới.

## Sử dụng nhanh

```python
from fbposter import FBClient, FBError

fb = FBClient.from_session_dir("sessions")   # hoặc from_cookies_txt("cookies.txt")

try:
    print(fb.verify())                       # đối chiếu USER_ID với c_user
    post = fb.create_post("Hello", audience="only_me")
    print(post["post_id"], post["permalink"])
    fb.edit_post(post["post_id"], text="Edited")
    fb.delete_post(post["post_id"])
except FBError as e:
    print("lỗi:", e)
finally:
    fb.close()
```

> [!IMPORTANT]
> `create_post` mặc định `audience="public"`. Truyền `audience=` tường minh
> hoặc `audience=None` để giữ mặc định tài khoản.

## API

| Method | Mô tả |
|---|---|
| `verify()` | Bóc token mới; đối chiếu `USER_ID` trong HTML với cookie `c_user`. |
| `create_post(text, images=None, audience="public", ai_generated=False, photo_ids=None)` | Đăng bài. Trả `{post_id, story_id, permalink (None nếu server không trả), photo_ids, session_id}`. `photo_ids` gắn ảnh đã upload, không upload lại. |
| `upload_photo(data, filename="")` | Upload 1 ảnh (bytes hoặc path) → `photoID`. |
| `list_posts(limit=10)` | Bài mới nhất trên profile. |
| `edit_post(post_id, text=None, audience=None, ai_generated=None)` | Sửa; nếu chỉ đổi audience/AI mà không đọc được text cũ → `FBError` (truyền `text=` tường minh). |
| `delete_post(post_id)` | Xoá bài. |
| `get_post_privacy(post_id)` | `EVERYONE` / `FRIENDS` / `SELF`... |

### Ảnh

- Tối đa **4 ảnh/bài** (cộng cả `photo_ids`) — vượt là raise `FBError`, không
  cắt âm thầm.
- Cap phía client **8MB**; server chốt cuối (live đã verify ≥5.05MB, 4K).
- JPEG/PNG/GIF/WEBP nhận qua magic bytes.
- Upload không gắn bài → ảnh nằm ngoài feed; dùng `photo_ids=` để gắn.

### doc_id cũ khi Facebook deploy

DevTools → Network → filter `graphql`, làm thao tác thật, tìm request có
`fb_api_req_friendly_name` tương ứng, copy `doc_id` sửa vào
`fbposter/spec.py`.

## Trạng thái

**Beta** (từ 1.1.0). API có thể đổi giữa các bản.

Đã có: permalink trung thực, verify đối chiếu user, audience kiểm trước
upload, giới hạn ảnh raise thay vì cắt, domain cookie khớp chặt, gắn
`photo_ids`. Còn làm: phân cấp exception, retry/backoff, CI, PyPI.

## Miễn trừ

Dùng cho mục đích giáo dục và tự động hoá cá nhân. Không liên quan Meta
Platforms, Inc. Tự động hoá có thể vi phạm điều khoản dịch vụ Facebook — bạn
tự chịu trách nhiệm cách dùng. Đừng dùng để spam, lừa đảo, đăng nội dung vi
phạm pháp luật. Tác giả không chịu trách nhiệm tổn thất tài khoản. Software
"as is", không bảo hành.

## License

[MIT](LICENSE)
