"""Test spec templates — offline."""
import base64

import pytest

from fbposter import spec


def test_story_id_roundtrip():
    short = spec.encode_story_id("100000000000001", "1677000000000001")
    assert short == "UzpfSTEwMDAwMDAwMDAwMDAwMToxNjc3MDAwMDAwMDAwMDAx"
    got = spec.decode_story_id(short)
    assert got == {"actor_id": "100000000000001",
                   "post_id": "1677000000000001"}
    long_id = spec.encode_story_id("100000000000001", "1677000000000001",
                                   long_form=True)
    assert long_id == ("UzpfSTEwMDAwMDAwMDAwMDAwMToxNjc3MDAwMDAwMDAwMDAx"
                       "OjE2NzcwMDAwMDAwMDAwMDE=")
    assert spec.decode_story_id(long_id)["post_id"] == "1677000000000001"


def test_privacy_map():
    assert spec.privacy("public")["privacy"]["base_state"] == "EVERYONE"
    assert spec.privacy("friends")["privacy"]["base_state"] == "FRIENDS"
    assert spec.privacy("only_me")["privacy"]["base_state"] == "SELF"
    with pytest.raises(ValueError):
        spec.privacy("nonsense")


def test_create_variables():
    v = spec.create_variables("hello", "100", ["PH1"], "public", "sess-1",
                              "1", "attr")
    inp = v["input"]
    assert inp["composer_type"] == "feed"
    assert inp["composer_entry_point"] == "inline_composer"
    assert inp["idempotence_token"].startswith("sess-1")
    assert inp["message"]["text"] == "hello"
    assert inp["attachments"] == [{"photo": {"id": "PH1"}}]
    assert inp["audience"]["privacy"]["base_state"] == "EVERYONE"
    assert inp["ai_generated_self_disclosure_metadata"] == {
        "was_self_disclosed_as_ai_generated": False}
    assert v["feedLocation"] == "NEWSFEED"
    assert v["renderLocation"] == "homepage_stream"
    assert "__relay_internal__pv__CometUFISingleLineUFIrelayprovider" in v


def test_create_variables_no_audience():
    v = spec.create_variables("x", "100", None, None, "s", "1", "a")
    assert "audience" not in v["input"]


def test_create_variables_ai_flag():
    v = spec.create_variables("x", "100", None, None, "s", "1", "a",
                              ai_generated=True)
    assert v["input"]["ai_generated_self_disclosure_metadata"] == {
        "was_self_disclosed_as_ai_generated": True}


def test_edit_variables():
    e = spec.edit_variables("new text", "LONGID", "100", None, "s", "3")
    assert e["input"]["composer_type"] == "edit"
    assert e["input"]["message"]["text"] == "new text"
    assert e["renderLocation"] == "permalink"
    assert "ai_generated_self_disclosure_metadata" not in e["input"]
    e2 = spec.edit_variables("x", "LONGID", "100", "friends", "s", "4",
                             ai_generated=True)
    assert e2["input"]["audience"]["privacy"]["base_state"] == "FRIENDS"
    assert e2["input"]["ai_generated_self_disclosure_metadata"] == {
        "was_self_disclosed_as_ai_generated": True}


def test_delete_variables():
    d = spec.delete_variables("LONGID", "100", "7")
    assert d["input"]["story_id"] == "LONGID"
    assert d["input"]["story_location"] == "PERMALINK"
    assert d["input"]["actor_id"] == "100"


def test_timeline_variables():
    t = spec.timeline_variables("100", 10, "CUR")
    assert t["feedLocation"] == "TIMELINE" and t["count"] == 10
    assert t["cursor"] == "CUR" and t["id"] == "100"


def test_privacy_query_variables():
    p = spec.privacy_query_variables("1677000000000001")
    assert base64.b64decode(p["id"]).decode() == \
        'privacy_scope_renderer:{"id":1677000000000001}'
    assert p["includePickerData"] is True and p["tags"] == []


def test_doc_ids_present():
    for key in ("ComposerStoryCreateMutation", "ComposerStoryEditMutation",
                "useCometFeedStoryDeleteMutation",
                "ProfileCometTimelineFeedRefetchQuery"):
        assert key in spec.DOC_IDS and spec.DOC_IDS[key].isdigit()
