# Changelog

## 1.0.0 — 2026-11-11

Bản đầu tiên.

- `FBClient`: đăng/sửa/xoá/liệt kê bài, verify session, upload ảnh
  (multipart dựng tay), đọc lại privacy bài đăng.
- Đối tượng xem: `public` / `friends` / `only_me` lúc tạo và lúc sửa.
- Nhãn AI generated: bật lúc tạo hoặc sau khi đăng.
- Bootstrap token từ 1 GET `www.facebook.com`; cache 30 phút.
- Thuần HTTPS: `curl_cffi` duy nhất, không browser.
