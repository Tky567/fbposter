# Changelog

## 1.1.0 — 2026-11-11

Sửa từ báo cáo thiết kế + bằng chứng test live. Không phá API trừ 1 điểm:
`permalink` có thể là `None`.

- **`permalink` trung thực** — `None` khi Facebook không trả url; hết
  permalink giả `https://www.facebook.com/me`.
- **`verify()` đối chiếu USER_ID** trong HTML với cookie `c_user` — cookie
  sai tài khoản bị từ chối ngay.
- **`audience` sai raise `FBError` trước khi upload** (hết `ValueError` lẫn
  trong hệ lỗi riêng, hết ảnh mồ côi).
- **Vượt 4 ảnh/bài raise** — không còn cắt âm thầm còn 4.
- **`create_post(images="<str>")` bọc 1 ảnh** — hết bug lặp theo ký tự.
- **`create_post(photo_ids=[...])` gắn ảnh đã upload** — không upload lại.
- **`from_cookies_txt` khớp domain chặt** — `evilfacebook.com` /
  `facebook.com.attacker.io` bị loại (POC của báo cáo).
- **Cap ảnh 8MB** (test live: FB nhận ≥5.05MB/7680×4320) — hạn chế tự chế
  5MB cũ đã mở.
- Python 3.10 import được (`typing.Self` chỉ có từ 3.11).
- `from_session_dir` nhận list cookie lẫn `{"cookies": [...]}`; `upload_photo`
  nhận đường dẫn; lỗi từng phần kèm data hợp lệ không coi là thất bại;
  nhận dạng `{error, errorSummary}`; 429/5xx có message riêng; `jazoest()`
  trả `str` đúng annotation; bỏ `_last_html` (giữ dữ liệu nhạy cảm vô ích).
- Metadata: classifier Beta, `curl_cffi>=0.7,<0.18`.

## 1.0.0 — 2026-11-11

Bản đầu tiên.

- `FBClient`: đăng/sửa/xoá/liệt kê bài, verify session, upload ảnh
  (multipart dựng tay), đọc lại privacy bài đăng.
- Đối tượng xem: `public` / `friends` / `only_me` lúc tạo và lúc sửa.
- Nhãn AI generated: bật lúc tạo hoặc sau khi đăng.
- Bootstrap token từ 1 GET `www.facebook.com`; cache 30 phút.
- Thuần HTTPS: `curl_cffi` duy nhất, không browser.
