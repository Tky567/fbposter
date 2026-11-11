"""Đăng 1 bài text — ví dụ tối giản."""
from fbposter import FBClient, FBError


def main() -> None:
    fb = FBClient.from_session_dir("sessions")
    try:
        print(fb.verify())
        r = fb.create_post("xin chào từ fbposter 🚀", audience="public")
        print("post_id :", r["post_id"])
        print("permalink:", r["permalink"])
    except FBError as e:
        print("lỗi:", e)
    finally:
        fb.close()


if __name__ == "__main__":
    main()
