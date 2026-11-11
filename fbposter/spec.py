"""Spec của GraphQL Facebook web — hằng số bóc từ traffic web thật
(các doc_id là định danh công khai của mutation, client web nào cũng dùng).
doc_id đổi khi FB deploy mutation mới — self-heal: nếu server trả lỗi
"doc_id not found" thì chụp lại mutation từ web rồi sửa hằng số ở đây.
"""
import base64
import json
import uuid

# ------------------------------------------------------------- mutation ids
DOC_IDS = {
    "ComposerStoryCreateMutation": "29374258312259175",
    "ComposerStoryEditMutation": "28958868797140406",
    "useCometFeedStoryDeleteMutation": "29100969972853465",
    "ProfileCometTimelineFeedRefetchQuery": "29524054653885841",
}

DOC_CREATE = DOC_IDS["ComposerStoryCreateMutation"]
DOC_EDIT = DOC_IDS["ComposerStoryEditMutation"]
DOC_DELETE = DOC_IDS["useCometFeedStoryDeleteMutation"]
DOC_TIMELINE = DOC_IDS["ProfileCometTimelineFeedRefetchQuery"]
DOC_PRIVACY = "30244314248502379"  # CometPrivacySelectorEditableQuery

# --------------------------------------------------------------- endpoints
GRAPHQL_URL = "https://www.facebook.com/api/graphql/"
UPLOAD_URL = "https://upload.facebook.com/ajax/react_composer/attachments/photo/upload"
HOME_URL = "https://www.facebook.com/"

# __crn theo surface nơi request phát ra
CRN = {
    "create": "comet.fbweb.CometHomeRoute",
    "edit": "comet.fbweb.CometSinglePostDialogRoute",
    "delete": "comet.fbweb.CometSinglePostDialogRoute",
    "timeline": "comet.fbweb.CometProfileTimelineListViewRoute",
    "upload": "comet.fbweb.CometHomeRoute",
}

# ------------------------------------------------------- relay provider gk
# __relay_internal__pv__* — GK cache của relay, nguyên văn từ request thật.
_CREATE_RELAY_FLAGS = {
    "__relay_internal__pv__GeminiUFISaveToKnowledgeHubGKrelayprovider": False,
    "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
    "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
    "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "AUTO_TRANSLATE",
    "__relay_internal__pv__IsWorkUserrelayprovider": False,
    "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
    "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
    "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
    "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
    "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
    "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
    "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
    "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
    "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
    "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
    "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
    "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
    "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
    "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
    "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
    "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
    "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
    "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
    "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    "__relay_internal__pv__groups_comet_use_glvrelayprovider": False,
    "__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider": True,
    "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider": True,
    "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider": False,
}

_EDIT_RELAY_FLAGS = {
    "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
    "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
    "__relay_internal__pv__IsWorkUserrelayprovider": False,
    "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
    "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
    "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
    "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
    "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
    "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
    "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
    "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
    "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
    "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
    "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
    "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
    "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "AUTO_TRANSLATE",
    "__relay_internal__pv__GeminiUFISaveToKnowledgeHubGKrelayprovider": False,
    "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
    "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
    "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
    "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
    "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
    "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
    "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
    "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    "__relay_internal__pv__CometComposerPPEAddCollaboratorsEnabledrelayprovider": False,
    "__relay_internal__pv__ProdashWebIGContentGKrelayprovider": False,
    "__relay_internal__pv__ContentLibraryStatusColumnGKrelayprovider": False,
    "__relay_internal__pv__ContentLibraryHighQualityPillGKrelayprovider": False,
    "__relay_internal__pv__ContentLibraryUnifiedContentStatusGKrelayprovider": True,
}

_TIMELINE_RELAY_FLAGS = {
    "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
    "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
    "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
    "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
    "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
    "__relay_internal__pv__IsWorkUserrelayprovider": False,
    "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
    "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
    "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
    "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
    "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
    "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
    "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
    "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
    "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
    "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
    "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
    "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "AUTO_TRANSLATE",
    "__relay_internal__pv__GeminiUFISaveToKnowledgeHubGKrelayprovider": False,
    "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
    "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
    "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
    "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
    "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
    "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
    "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
    "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
}

# ------------------------------------------------------- privacy base_state
PRIVACY_BASE_STATE = {
    "public": "EVERYONE",
    "friends": "FRIENDS",
    "only_me": "SELF",
}

# -------------------------------------------------------- upload multipart
# file part: ("farr", (filename, bytes, mime)) — source=8 = react composer,
# waterfallxapp=comet, profile_id=actor. Ghép trong client.upload_photo.

# ----------------------------------------------------------- templates
def new_session_id() -> str:
    return str(uuid.uuid4())


def new_idempotence_token(session_id: str) -> str:
    return f"{session_id}_FEED"


def privacy(audience: str | None) -> dict | None:
    """Audience block cho input. None → không gửi (dùng default tài khoản)."""
    if audience is None:
        return None
    base = PRIVACY_BASE_STATE.get(audience)
    if not base:
        raise ValueError(f"audience không hợp lệ: {audience} "
                         "(public | friends | only_me)")
    return {"privacy": {"allow": [], "base_state": base, "deny": [],
                        "tag_expansion_state": "UNSPECIFIED"}}


def create_variables(text: str, actor_id: str, photo_ids: list[str] | None,
                     audience: str | None, session_id: str,
                     mutation_id: str, attribution: str,
                     ai_generated: bool = False) -> dict:
    input_: dict = {
        "composer_entry_point": "inline_composer",
        "composer_source_surface": "newsfeed",
        "composer_type": "feed",
        "idempotence_token": new_idempotence_token(session_id),
        "source": "WWW",
        "ai_generated_self_disclosure_metadata": {
            "was_self_disclosed_as_ai_generated": ai_generated,
        },
        "message": {"ranges": [], "text": text},
        "inline_activities": [],
        "text_format_preset_id": "0",
        "publishing_flow": {"supported_flows":
                            ["ASYNC_SILENT", "ASYNC_NOTIF", "FALLBACK"]},
        "reels_remix": {"is_original_audio_reusable": True,
                        "remix_status": "ENABLED"},
        "post_publish_story_data": {"reshare_post_as_sticker": "DISABLED"},
        "logging": {"composer_session_id": session_id},
        "navigation_data": {"attribution_id_v2": attribution},
        "tracking": [None],
        "event_share_metadata": {"surface": "newsfeed"},
        "actor_id": actor_id,
        "client_mutation_id": mutation_id,
    }
    if audience is not None:
        input_["audience"] = privacy(audience)
    if photo_ids:
        input_["attachments"] = [{"photo": {"id": pid}} for pid in photo_ids]
    top = {
        "feedLocation": "NEWSFEED",
        "feedbackSource": 1,
        "focusCommentID": None,
        "gridMediaWidth": None,
        "groupID": None,
        "scale": 1,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "checkPhotosToReelsUpsellEligibility": True,
        "referringStoryRenderLocation": None,
        "renderLocation": "homepage_stream",
        "useDefaultActor": False,
        "inviteShortLinkKey": None,
        "isFeed": True,
        "isFundraiser": False,
        "isFunFactPost": False,
        "isGroup": False,
        "isEvent": False,
        "isTimeline": False,
        "isSocialLearning": False,
        "isPageNewsFeed": False,
        "isProfileReviews": False,
        "isWorkSharedDraft": False,
    }
    top.update(_CREATE_RELAY_FLAGS)
    top["input"] = input_
    return top


def edit_variables(text: str, story_id: str, actor_id: str,
                   audience: str | None, session_id: str,
                   mutation_id: str,
                   ai_generated: bool | None = None) -> dict:
    input_: dict = {
        "composer_entry_point": "edit_story",
        "composer_source_surface": "feed_story",
        "composer_type": "edit",
        "story_id": story_id,
        "message": {"ranges": [], "text": text},
        "with_tags_ids": [],
        "text_format_preset_id": "0",
        "reels_remix": {"is_original_audio_reusable": True,
                        "remix_status": "ENABLED"},
        "post_publish_story_data": {"reshare_post_as_sticker": "DISABLED"},
        "tracking": [None],
        "logging": {"composer_session_id": session_id},
        "editable_post_feature_capabilities": ["CONTAINED_LINK",
                                               "CONTAINED_MEDIA", "POLL"],
        "actor_id": actor_id,
        "client_mutation_id": mutation_id,
    }
    if audience is not None:
        input_["audience"] = privacy(audience)
    if ai_generated is not None:
        input_["ai_generated_self_disclosure_metadata"] = {
            "was_self_disclosed_as_ai_generated": ai_generated,
        }
    top = {
        "feedLocation": "NEWSFEED",
        "feedbackSource": 1,
        "focusCommentID": None,
        "scale": 1,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "referringStoryRenderLocation": None,
        "renderLocation": "permalink",
        "useDefaultActor": False,
        "isGroupViewerContent": False,
        "shouldFetchProDashContentLibraryStory": False,
        "isSocialLearning": False,
        "isWorkDraftFor": False,
        "ppeEnabled": False,
        "isStarsEdited": False,
    }
    top.update(_EDIT_RELAY_FLAGS)
    top["input"] = input_
    return top


def delete_variables(story_id: str, actor_id: str, mutation_id: str) -> dict:
    return {
        "input": {
            "story_id": story_id,
            "story_location": "PERMALINK",
            "actor_id": actor_id,
            "client_mutation_id": mutation_id,
        },
        "groupID": None,
        "inviteShortLinkKey": None,
        "renderLocation": None,
        "scale": 1,
        "__relay_internal__pv__groups_comet_use_glvrelayprovider": False,
    }


def timeline_variables(actor_id: str, count: int,
                       cursor: str | None = None) -> dict:
    top = {
        "afterTime": None,
        "beforeTime": None,
        "count": count,
        "cursor": cursor,
        "feedLocation": "TIMELINE",
        "feedbackSource": 0,
        "focusCommentID": None,
        "memorializedSplitTimeFilter": None,
        "omitPinnedPost": True,
        "postedBy": None,
        "privacy": None,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "referringStoryRenderLocation": None,
        "renderLocation": "timeline",
        "run_with_continuation_key": True,
        "scale": 1,
        "stream_count": 1,
        "taggedInOnly": None,
        "trackingCode": None,
        "useDefaultActor": False,
        "id": actor_id,
    }
    top.update(_TIMELINE_RELAY_FLAGS)
    return top


def privacy_query_variables(post_id: str) -> dict:
    """CometPrivacySelectorEditableQuery — đọc base_state hiện tại của bài.
    id = base64('privacy_scope_renderer:{"id":<post_id>}') (từ traffic web)."""
    return {
        "includePickerData": True,
        "localPrivacyRow": None,
        "renderLocation": "COMET_STORY_EDIT_COMPOSER",
        "scale": 1,
        "tags": [],
        "id": base64.b64encode(
            f'privacy_scope_renderer:{{"id":{post_id}}}'.encode()).decode(),
    }


# ------------------------------------------------------------- story ids

def encode_story_id(actor_id: str, post_id: str, long_form: bool = False) -> str:
    """S:_I<actor>:<post> — thêm ':<post>' cho dạng edit/delete dùng."""
    raw = f"S:_I{actor_id}:{post_id}"
    if long_form:
        raw = f"{raw}:{post_id}"
    return base64.b64encode(raw.encode()).decode()


def decode_story_id(story_id: str) -> dict:
    """base64 'S:_I<actor>:<post>[:<post>]' → {actor_id, post_id}."""
    try:
        raw = base64.b64decode(story_id).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — id lạ giữ nguyên
        return {"actor_id": "", "post_id": ""}
    parts = raw.split(":")
    if len(parts) >= 3:
        actor = parts[1].removeprefix("_I")
        return {"actor_id": actor, "post_id": parts[2]}
    return {"actor_id": "", "post_id": ""}


def json_compact(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))
