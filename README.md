<div align="center">

# fbposter

**An unofficial, browser-less Python client for posting to and managing posts on your own Facebook profile.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](#project-status)
[![Unofficial](https://img.shields.io/badge/Meta-unofficial-red.svg)](#disclaimer)

English · [Tiếng Việt](README.vi.md)

</div>

> [!WARNING]
> **This is an unofficial library that automates a personal Facebook account.**
> It is not affiliated with, endorsed by, or supported by Meta. Automating an
> account can violate Facebook's Terms of Service and may lead to a checkpoint,
> restrictions, or a permanent ban. Use it only on **your own account**, at a
> **low, human-like pace**, and at **your own risk**. See [Disclaimer](#disclaimer).

---

## Table of contents

- [Why does this exist?](#why-does-this-exist)
- [Features](#features)
- [Installation](#installation)
- [Getting your cookies](#getting-your-cookies)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Error handling](#error-handling)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Project status](#project-status)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [License](#license)

## Why does this exist?

Facebook's official Graph API no longer lets third-party apps publish to a
**personal profile** timeline. The only way to post there is through the web
composer. `fbposter` talks to the same internal GraphQL and upload endpoints
the web client uses, with plain HTTPS requests and a Chrome TLS fingerprint
(via [`curl_cffi`](https://github.com/lexiforest/curl_cffi)) — no Selenium,
no Playwright, no browser to keep running.

Because those endpoints are private and undocumented, **they can change
without notice**. See [Project status](#project-status) and
[Troubleshooting](#troubleshooting).

## Features

- Create text posts and posts with up to 4 photos
- Choose the audience: public, friends, or only me
- Toggle the "AI generated" disclosure label
- Attach already-uploaded photo IDs (`photo_ids=`) without re-uploading
- List, edit, and delete your own posts
- Read a post's current privacy setting
- Load cookies from a JSON session directory, a Python list, or a
  `cookies.txt` (Netscape) export
- Single runtime dependency: `curl_cffi`
- Python 3.10+

## Installation

The package is not on PyPI yet. Install from source:

```bash
pip install git+https://github.com/Tky567/fbposter.git
```

or from a local clone:

```bash
git clone https://github.com/Tky567/fbposter.git
cd fbposter
pip install .
```

## Getting your cookies

`fbposter` authenticates with the cookies of a logged-in Facebook web session.
At minimum you need **`c_user`** and **`xs`**. Including `datr` is recommended.

> [!CAUTION]
> These cookies grant full access to your account. Treat them like a password.
> Never paste them into issues, chats, or commit them to git.
> See [Security](#security).

### Option A — copy from browser DevTools

1. Log in to <https://www.facebook.com> in your browser.
2. Open DevTools (`F12`) → **Application** (Chrome/Edge) or **Storage**
   (Firefox) → **Cookies** → `https://www.facebook.com`.
3. Copy the **Value** of `c_user`, `xs`, and (optionally) `datr`.
4. Save them as a JSON file inside a `sessions/` folder, for example
   `sessions/facebook_main.json`:

```json
[
  {"name": "c_user", "value": "YOUR_USER_ID"},
  {"name": "xs",     "value": "YOUR_XS_COOKIE"},
  {"name": "datr",   "value": "YOUR_DATR_COOKIE"}
]
```

`{"cookies": [ ... ]}` is accepted as well.

### Option B — export a `cookies.txt`

Use a cookie-export browser extension that writes the Netscape `cookies.txt`
format, then load it directly (see [Quick start](#quick-start)). Only
`*.facebook.com` cookies are read; cookies for other sites in the file are
ignored.

> Logging out of Facebook, changing your password, or Facebook rotating the
> session will invalidate the cookies. Export fresh ones when that happens.

## Quick start

```python
from fbposter import FBClient, FBError

fb = FBClient.from_session_dir("sessions")   # or from_cookies_txt("cookies.txt")

try:
    print(fb.verify())
    # {'ok': True, 'user_id': '...', 'name': '...', 'dtsg_len': ..., 'rev': '...'}

    post = fb.create_post("Hello from fbposter", audience="only_me")
    print(post["post_id"], post["permalink"])

    fb.edit_post(post["post_id"], text="Edited text")
    fb.delete_post(post["post_id"])
except FBError as e:
    print("Facebook error:", e)
finally:
    fb.close()
```

`FBClient` is also a context manager:

```python
with FBClient.from_cookies_txt("cookies.txt") as fb:
    fb.create_post("Hello", audience="friends")
```

> [!IMPORTANT]
> `create_post` defaults to `audience="public"`. Always pass `audience=`
> explicitly, or pass `audience=None` to keep your account's default.

More runnable scripts are in [`examples/`](examples/).

## API reference

### Creating a client

| Constructor | Description |
|---|---|
| `FBClient(cookies, http=None, impersonate="chrome")` | `cookies` is a list of `{"name", "value"}` dicts or a `{name: value}` dict. Requires `c_user` and `xs`. `http` lets you pass your own `curl_cffi` session. |
| `FBClient.from_session_dir(directory)` | Reads the last `facebook_*.json` (by file name) in the directory (falls back to any `*.json`). The file may be a list of cookies or `{"cookies": [...]}`. |
| `FBClient.from_cookies_txt(path)` | Reads a Netscape `cookies.txt`. Handles `# HttpOnly_` lines. |

### Methods

| Method | Returns | Description |
|---|---|---|
| `verify()` | `dict` | Fetches fresh tokens and returns `{ok, user_id, name, dtsg_len, rev}`. Cross-checks the `USER_ID` served in the HTML against your `c_user` cookie; raises `FBError` on mismatch or dead session. |
| `create_post(text, images=None, audience="public", ai_generated=False, photo_ids=None)` | `dict` | Publishes a post. Returns `post_id`, `story_id`, `permalink` (`None` if Facebook does not return one), `photo_ids`, `session_id`. `images` is a list of paths or `bytes` (a single path/bytes is also accepted). `photo_ids` attaches IDs already uploaded via `upload_photo` without re-uploading. |
| `upload_photo(data, filename="")` | `str` | Uploads one image (`bytes` or a file path) and returns its photo ID. |
| `list_posts(limit=10)` | `list[dict]` | Newest-first posts on your profile: `post_id`, `story_id`, `text`, `time`, `permalink`. Pinned posts are not included. |
| `edit_post(post_id, text=None, audience=None, ai_generated=None)` | `dict` | Edits text, audience, and/or the AI label. At least one is required. |
| `delete_post(post_id)` | `True` | Deletes a post. Raises `FBError` if Facebook does not confirm. |
| `get_post_privacy(post_id)` | `str \| None` | Current audience: `EVERYONE`, `FRIENDS`, `SELF`, ... |
| `close()` | `None` | Closes the underlying HTTP session. |

### Audience values

| `audience` | Meaning | Server `base_state` |
|---|---|---|
| `"public"` | Anyone | `EVERYONE` |
| `"friends"` | Friends only | `FRIENDS` |
| `"only_me"` | Only you | `SELF` |
| `None` | Keep the account default | *(not sent)* |

### Images

- Up to **4 images** per post (`uploaded + photo_ids` combined). Exceeding the
  limit raises `FBError` — nothing is silently dropped.
- Each image must pass the client-side cap of **8 MB** (the server has the
  final say; uploads of 5 MB+ 4K images are verified to work) and be a
  **JPEG, PNG, GIF, or WEBP** (detected from the file's magic bytes, not its
  extension).
- Uploading without attaching the photo to a post leaves it in your
  unattached photo bucket — use `photo_ids=` in `create_post` to attach it.

### Editing notes

`edit_post` must send the full post text. When you change only `audience` or
`ai_generated`, the current text is looked up in your 50 most recent posts.
If it cannot be found (for example an old or pinned post), `FBError` is raised
instead of risking an empty overwrite — pass `text=...` explicitly in that
case. Editing also resets mentions and tags in the post text.

## Error handling

Every failure raises `fbposter.FBError` (a `RuntimeError`) with the server's
message. It carries optional `.code` and `.subcode` attributes.

```python
from fbposter import FBClient, FBError

try:
    fb.create_post("hi", audience="friends")
except FBError as e:
    print(e, e.code)
```

There is currently a single exception class; a finer-grained hierarchy
(session expired, rate limited, outdated spec) is on the [roadmap](#project-status).

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| `session facebook hết hạn hoặc checkpoint` / session expired | Cookies are expired, logged out, or Facebook requires verification | Open Facebook in a browser, resolve any checkpoint, then export fresh cookies |
| `thiếu cookie c_user, xs` | Missing required cookies | Make sure both `c_user` and `xs` are present |
| `không có session facebook trong ...` | No `*.json` in the directory | Check the folder path and file name |
| `không bóc được fb_dtsg từ home` | Restricted session or Facebook changed the page | Re-export cookies; if it persists, the page format may have changed |
| `facebook từ chối ...` with a server message | Facebook rejected the request (possibly an outdated `doc_id`) | See [Updating `doc_id`s](#updating-doc_ids) |
| HTTP 429 | Rate limited | Stop, wait, and slow down |
| `không đọc được nội dung hiện tại của bài` | `edit_post` could not find the old text | Pass `text=` explicitly |
| `ảnh vượt 8MB` / `ảnh không hợp lệ` | Image too large or not a supported format | Resize or convert the image |
| `cookie không khớp tài khoản đang đăng nhập` | Cookies from another logged-in account | Export cookies from the account you intend to use |

Error messages are currently in Vietnamese; the table above lists the
original text so you can match it.

### Updating `doc_id`s

Facebook identifies each GraphQL operation with a numeric `doc_id` that
changes when it deploys a new build. When an operation starts failing:

1. Open facebook.com, open DevTools → **Network**, filter by `graphql`.
2. Perform the action manually (create, edit, delete a post…).
3. Find the request whose `fb_api_req_friendly_name` matches (for example
   `ComposerStoryCreateMutation`) and copy its `doc_id`.
4. Update the constant in [`fbposter/spec.py`](fbposter/spec.py).

## Security

Your session cookie is equivalent to your password.

- Keep session files **out of version control**. The bundled `.gitignore`
  excludes `sessions/`, `cookies.txt`, `facebook_*.json`, `*.session.json`,
  `*cookie*.json`, and `.env` — still double-check before every commit.
- Restrict file permissions, e.g. `chmod 600 sessions/*.json`.
- Never share cookies in issues, screenshots, logs, or CI output.
- If a cookie leaks: log out of Facebook on all devices and change your
  password to invalidate it.
- `verify()` rejects cookies whose `c_user` does not match the account
  actually logged in on the served page — a small guard against mixing up
  exports.
- Prefer a dedicated account for experimentation.

## How it works

1. One `GET https://www.facebook.com/` bootstraps the request tokens
   (`fb_dtsg`, `lsd`, `__rev`, …), cached for 30 minutes.
2. Operations are `POST`s to `https://www.facebook.com/api/graphql/` using the
   same `doc_id` and variables shape as the web composer.
3. Photos are uploaded as multipart to `upload.facebook.com`, then referenced
   by ID when creating the post.
4. `curl_cffi` impersonates Chrome's TLS fingerprint.

## Limitations

- Personal profile only — no Pages, Groups, Reels, video, or Stories.
- No mentions, link attachments, polls, or scheduling.
- Synchronous API only.
- No automatic retries, backoff, or token refresh yet.
- Depends on private endpoints; **breakage after a Facebook deploy is
  expected** and may require a manual `doc_id` update.
- Using Chrome TLS impersonation does **not** make automation undetectable.

## Project status

**Beta** (since 1.1.0). The public API may change between releases.

Changelog highlights in 1.1.0: honest `permalink` (`None` instead of a fake
`/me` URL), `verify()` cross-checking, audience validated before uploads,
image-limit raise instead of silent truncation, strict `cookies.txt` domain
matching, and `photo_ids=` attachment.

Planned:

- [ ] Fine-grained exception hierarchy
- [ ] Retry / backoff and automatic token refresh
- [ ] Offline test suite and CI
- [ ] Centralised, overridable `doc_id` configuration
- [ ] Publish to PyPI

## Contributing

Issues and pull requests are welcome.

- Bug reports: include your Python version, the exact error, and the
  operation that failed. **Remove all cookies and tokens first.**
- When Facebook changes something, a PR updating `doc_id`s in
  `fbposter/spec.py` with the operation name is the most useful contribution.
- Code style: `ruff check .` (configured in `pyproject.toml`).

## Disclaimer

This project is provided for educational and personal-automation purposes.
It is **not** affiliated with or endorsed by Meta Platforms, Inc.; Facebook is
a trademark of its owner. Automated access may violate Facebook's Terms of
Service and can result in account restrictions or bans. You are solely
responsible for how you use this software and for complying with applicable
laws and platform rules. Do not use it to spam, harass, deceive, or post
unlawful content. The authors accept no liability for any damage or loss of
account access. Software is provided "as is" without warranty.

## License

[MIT](LICENSE)
