"""Test FBClient end-to-end trên transport giả — offline hoàn toàn."""
import json
from urllib.parse import parse_qs

import pytest

from fbposter import FBClient, FBError, spec

from .conftest import ACTOR, DTSG_A, LSD, PNG, decode_form


def test_verify(fb, fake):
    info = fb.verify()
    assert info["ok"] and info["user_id"] == ACTOR
    assert fake.cookies.cookies["c_user"] == ACTOR


def test_create_post_full(fb, fake):
    fake.responses = {
        "ComposerStoryCreateMutation": json.dumps({
            "data": {"story_create": {
                "publishing_flow": "FALLBACK",
                "story": {"id": "UzpfSTEwMDAwMDAwMDAwMDAwMToxNjc3MDAwMDAwMDAwMDAx",
                          "legacy_story_hideable_id": "1677000000000001",
                          "url": "https://www.facebook.com/user/posts/"
                                 "pfbidTEST",
                          "default_actor": {"id": ACTOR}}}}}),
    }
    upload_calls = []

    def fake_upload(url, params, parts, headers):
        upload_calls.append({"url": url, "params": params, "parts": parts,
                             "headers": headers})
        return type("R", (), {"text": json.dumps(
            {"payload": {"photoID": "1677000000000009"}}),
            "status_code": 200, "ok": True})()

    fb._post_upload = fake_upload
    r = fb.create_post("hello world", images=[PNG], audience="public")
    assert r["post_id"] == "1677000000000001"
    assert r["permalink"].startswith("https://www.facebook.com/")
    assert r["photo_ids"] == ["1677000000000009"]

    # multipart upload đúng spec
    upload = upload_calls[0]
    assert upload["url"].startswith("https://upload.facebook.com/"
                                    "ajax/react_composer/attachments/"
                                    "photo/upload")
    parts = {p[0]: p[1] for p in upload["parts"]}
    assert parts.get("source") == "8"
    assert parts.get("profile_id") == ACTOR
    assert parts.get("waterfallxapp") == "comet"
    farr = parts.get("farr")
    assert isinstance(farr, tuple) and farr[0].endswith(".png") \
        and farr[1] == PNG and farr[2] == "image/png"
    up_params = upload["params"]
    assert up_params.get("__user") == ACTOR
    assert up_params.get("fb_dtsg") == DTSG_A
    assert "jazoest" in up_params and "lsd" in up_params

    # graphql create
    create = fake.posts[0]
    assert create["url"] == "https://www.facebook.com/api/graphql/"
    assert create["headers"]["x-fb-friendly-name"] == \
        "ComposerStoryCreateMutation"
    assert create["headers"]["x-fb-lsd"] == LSD
    body = {k: v[0] for k, v in parse_qs(
        decode_form(create), keep_blank_values=True).items()}
    assert body["doc_id"] == spec.DOC_CREATE
    assert body["fb_dtsg"] == DTSG_A
    assert body["__user"] == ACTOR
    assert body["jazoest"] == "22877"
    variables = json.loads(body["variables"])
    assert variables["input"]["composer_type"] == "feed"
    assert variables["input"]["attachments"] == [
        {"photo": {"id": "1677000000000009"}}]
    assert variables["input"]["audience"]["privacy"]["base_state"] == \
        "EVERYONE"


def test_list_posts(fb, fake):
    fake.responses = {
        "ProfileCometTimelineFeedRefetchQuery": json.dumps({
            "data": {"node": {"timeline_list_feed_units": {
                "edges": [
                    {"node": {"post_id": "111",
                              "creation_time": 1794373849,
                              "permalink_url": "/user/posts/111",
                              "message": {"text": "hello"}},
                     "cursor": "CUR1"},
                    {"node": {"post_id": "222",
                              "creation_time": 1794373900,
                              "permalink_url": "/user/posts/222",
                              "message": {"text": "world"}}},
                ],
                "page_info": {}}}}}),
    }
    posts = fb.list_posts(limit=5)
    assert [p["post_id"] for p in posts] == ["111", "222"]
    assert posts[0]["permalink"].endswith("/posts/111")
    assert posts[0]["text"] == "hello"


def test_get_post_privacy(fb, fake):
    fake.responses = {
        "CometPrivacySelectorEditableQuery": json.dumps({
            "data": {"node": {"privacy_row_input": {
                "allow": [], "base_state": "FRIENDS", "deny": [],
                "tag_expansion_state": "UNSPECIFIED"}}}}),
    }
    assert fb.get_post_privacy("1677000000000001") == "FRIENDS"
    pcall = fake.posts[-1]
    pbody = {k: v[0] for k, v in parse_qs(
        decode_form(pcall), keep_blank_values=True).items()}
    assert pbody["doc_id"] == spec.DOC_PRIVACY
    pvars = json.loads(pbody["variables"])
    import base64
    assert base64.b64decode(pvars["id"]).decode() == \
        'privacy_scope_renderer:{"id":1677000000000001}'


def test_edit_post(fb, fake):
    fake.responses = {
        "ComposerStoryEditMutation": json.dumps({
            "data": {"story_edit": {"story": {
                "message": {"text": "edited text"}}}}}),
    }
    er = fb.edit_post("1677000000000001", text="edited text")
    assert er["story_id"].startswith("UzpfSTE")
    edit_call = fake.posts[-1]
    ebody = {k: v[0] for k, v in parse_qs(
        decode_form(edit_call), keep_blank_values=True).items()}
    assert ebody["doc_id"] == spec.DOC_EDIT
    evars = json.loads(ebody["variables"])
    assert spec.decode_story_id(
        evars["input"]["story_id"])["post_id"] == "1677000000000001"
    assert evars["input"]["composer_type"] == "edit"


def test_delete_post(fb, fake):
    fake.responses = {
        "useCometFeedStoryDeleteMutation": json.dumps({
            "data": {"story_delete": {
                "deleted_story_id":
                    "UzpfSTEwMDAwMDAwMDAwMDAwMToxNjc3MDAwMDAwMDAwMDAx"
                    "OjE2NzcwMDAwMDAwMDAwMDE="}}}),
    }
    assert fb.delete_post("1677000000000001") is True
    dcall = fake.posts[-1]
    dbody = {k: v[0] for k, v in parse_qs(
        decode_form(dcall), keep_blank_values=True).items()}
    assert dbody["doc_id"] == spec.DOC_DELETE
    dvars = json.loads(dbody["variables"])
    assert dvars["input"]["story_location"] == "PERMALINK"


def test_error_session_expired(fb, fake):
    fake.responses = {
        "ComposerStoryCreateMutation": json.dumps({
            "errors": [{"message": "Session expired", "code": 1357001}]}),
    }
    with pytest.raises(FBError, match="Session expired"):
        fb.create_post("hi")


def test_error_dead_session(fake):
    fake.home_html = "<html><form name='login'></form></html>"
    fb = FBClient({"c_user": ACTOR, "xs": "SYNTHETIC_XS_VALUE", "datr": "d"},
                  http=fake)
    with pytest.raises(FBError):
        fb.verify()


def test_empty_post_raises(fb):
    with pytest.raises(FBError, match="trống"):
        fb.create_post("   ")


def test_parse_docs():
    resp = type("R", (), {"text":
                  'for (;;);{"data":{"a":1},"extensions":{"is_final":true}}'
                  '{"data":{"b":2}}  {"x":3}',
                  "status_code": 200, "ok": True})()
    docs = FBClient._parse_docs(resp)
    assert len(docs) == 3
    assert docs[0]["data"] == {"a": 1}
    assert docs[1]["data"] == {"b": 2}
    assert docs[2] == {"x": 3}


def test_sniff_image():
    from fbposter.client import sniff_image
    assert sniff_image(PNG) == ("image/png", ".png")
    assert sniff_image(b"\xff\xd8\xffxyz") == ("image/jpeg", ".jpg")
    assert sniff_image(b"not an image") is None


def test_multipart_roundtrip():
    from fbposter.client import build_multipart
    body, boundary = build_multipart([
        ("source", "8"),
        ("farr", ("a.png", PNG, "image/png")),
    ])
    assert boundary.startswith("----WebKitFormBoundary")
    assert f"--{boundary}\r\n".encode() in body
    assert f"--{boundary}--\r\n".encode() in body
    assert b'name="source"' in body
    assert b'name="farr"; filename="a.png"' in body
    assert b"Content-Type: image/png" in body
