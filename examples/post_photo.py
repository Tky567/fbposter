"""Đăng bài kèm ảnh + đối tượng xem + nhãn AI."""
import sys
from pathlib import Path

from fbposter import FBClient, FBError


def main() -> None:
    images = [Path(p) for p in sys.argv[1:]]
    fb = FBClient.from_session_dir("sessions")
    try:
        r = fb.create_post(
            "kèm ảnh từ fbposter",
            images=images or None,
            audience="public",        # public | friends | only_me
            ai_generated=False,       # True → gắn nhãn "AI generated"
        )
        print("photo_ids:", r["photo_ids"])
        print("post_id  :", r["post_id"])
        print("permalink:", r["permalink"])
        print("privacy  :", fb.get_post_privacy(r["post_id"]))
    except FBError as e:
        print("lỗi:", e)
    finally:
        fb.close()


if __name__ == "__main__":
    main()
