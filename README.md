# fbposter

Đăng bài và quản lí bài đăng lên Facebook profile cá nhân **thuần HTTPS** —
không browser, không playwright, không selenium. Chỉ `curl_cffi` (TLS
fingerprint Chrome) gọi `facebook.com`.

Thư viện nói chuyện trực tiếp với các endpoint GraphQL + upload của Facebook
web composer, cùng giao thức mà trình duyệt gửi. Một GET `www.facebook.com`
để bootstrap token (`fb_dtsg`, `lsd`, `__rev`...), mọi request sau đó là HTTPS
thuần.

## Cài đặt

```bash
pip install fbposter
```

Yêu cầu Python ≥ 3.10, duy nhất một dependency runtime: `curl_cffi`.

## Session

Cần cookie đăng nhập Facebook (`c_user` + `xs`). Thư viện đọc từ thư mục
session dạng JSON:

```json
[
  {"name": "c_user", "value": "YOUR_USER_ID"},
  {"name": "xs", "value": "..."},
  {"name": "datr", "value": "..."}
]
```

> **Không bao giờ commit thư mục session lên git.** `.gitignore` đã chặn
> `sessions/`; nếu đặt session ở chỗ khác, tự thêm vào ignore.

```python
from fbposter import FBClient

fb = FBClient.from_session_dir("sessions")
```

Có thể truyền cookie trực tiếp thay vì file:

```python
fb = FBClient([{"name": "c_user", "value": "..."},
               {"name": "xs", "value": "..."}])
```

Hoặc thẳng từ file `cookies.txt` (Netscape format — tiện ích
*Get cookies.txt LOCALLY*, *EditThisCookie*...). Loader chỉ lấy cookie
`*.facebook.com`, tự xử lý dòng `# HttpOnly_`:

```python
fb = FBClient.from_cookies_txt("cookies.txt")
```

File export toàn trang (kèm discord/google/...) vẫn dùng được — các cookie
domain khác bị bỏ qua. Đã test live: `c_user + xs + datr + fr...` trong
export là đủ, không cần thứ gì thêm.

## Sử dụng

```python
from fbposter import FBClient

fb = FBClient.from_session_dir("sessions")

fb.verify()
# → {"ok": True, "user_id": "...", "name": "...", "rev": "..."}

r = fb.create_post("hello world")
# → {"post_id", "story_id", "permalink", "photo_ids"}

r = fb.create_post("kèm ảnh", images=["a.png", "b.jpg"],
                   audience="public", ai_generated=False)
# → {post_id, story_id, permalink (None nếu server không trả), photo_ids}

# gắn photoID đã upload sẵn — không upload lại
pid = fb.upload_photo(open("c.jpg", "rb").read(), "c.jpg")
fb.create_post("gắn ảnh có sẵn", photo_ids=[pid])

fb.list_posts(limit=10)
# → [{"post_id", "text", "time", "permalink", "story_id"}]

fb.edit_post(r["post_id"], text="nội dung mới")
fb.edit_post(r["post_id"], audience="friends")       # đổi đối tượng xem
fb.edit_post(r["post_id"], ai_generated=True)        # gắn nhãn AI

fb.get_post_privacy(r["post_id"])                    # → EVERYONE/FRIENDS/SELF

fb.delete_post(r["post_id"])                         # → True
```

### Đối tượng xem (`audience`)

| giá trị | ý nghĩa | base_state server |
|---|---|---|
| `"public"` | mọi người | `EVERYONE` |
| `"friends"` | bạn bè | `FRIENDS` |
| `"only_me"` | chỉ mình tôi | `SELF` |
| `None` | giữ nguyên mặc định tài khoản | — |

Đặt lúc tạo (`create_post`) hoặc đổi sau (`edit_post`). Đọc lại state thật
trên server bằng `get_post_privacy()`.

### Nhãn AI generated

`create_post(..., ai_generated=True)` hoặc `edit_post(id, ai_generated=True)`
gắn nhãn "AI generated" của composer — flag nằm trong
`input.ai_generated_self_disclosure_metadata.was_self_disclosed_as_ai_generated`.

### Upload ảnh

`upload_photo(data_or_path)` upload 1 ảnh, trả `photoID`. `create_post` gọi
tự động khi có `images=`. JPEG/PNG/GIF/WEBP nhận qua magic bytes. Multipart
được dựng tay đúng định dạng web client (source=8, profile_id, waterfallxapp,
farr...).

Giới hạn ảnh:

- tối đa **4 ảnh/bài** — vượt là raise `FBError`, không cắt âm thầm.
- cap phía client **8MB** (cap server là chốt cuối). Facebook thật nhận được
  ít nhất 5.05MB / 7680×4320 JPEG — đã test live.
- `upload_photo` không đính kèm bài nào → ảnh nằm ngoài feed (không có API
  xoá ảnh mồ côi trong thư viện); dùng `photo_ids=` trong `create_post` để
  gắn ảnh đã upload.

`permalink` trả `None` nếu Facebook không gửi url — không có permalink giả.

## Xử lí lỗi

Mọi lỗi HTTP/GraphQL raise `fbposter.FBError` kèm message gốc của server
("Session expired", "doc_id not found"...). Session chết → thông báo rõ để
grab lại cookie. doc_id mutation đổi khi Facebook deploy bản mới → chụp lại
traffic web, sửa hằng số `DOC_IDS` trong `fbposter/spec.py`.

## Kiểm tra

Thư viện phát hành không kèm test offline — bộ test offline chạy tại
workspace (selftest + pytest trên transport giả, không gọi facebook.com).

## Bảo mật phiên

Cookie `c_user` + `xs` = toàn quyền tài khoản:

- đừng commit, đừng dán vào issue/log CI; file cookie để permission chặt
  (Windows: chỉ user của bạn đọc được).
- đăng xuất hoặc đổi mật khẩu → cookie chết; cuộn lại cookie mới khi cần.
- thư viện đối chiếu `USER_ID` trong HTML với `cookie c_user` — cookie kéo
  từ tài khoản khác bị từ chối ngay khi verify.

## Disclaimer

Thư viện tự động hoá thao tác trên **tài khoản của chính bạn**. Chịu rủi ro
tự chịu: automation vi phạm điều khoản dịch vụ Facebook có thể dẫn đến
checkpoint hoặc khoá tài khoản — dùng nhịp chậm, đừng spam, đừng retry dồn
dập. Không dùng để đăng nội dung vi phạm pháp luật. Tác giả không chịu trách
nhiệm cho cách dùng của người khác.

## License

MIT — xem [LICENSE](LICENSE).
