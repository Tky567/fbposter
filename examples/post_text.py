"""Đăng 1 bài text — ví dụ tối giản."""
from fbposter import FBClient, FBError


def main() -> None:
    fb = FBClient.from_session_dir("sessions")
    try:
        print(fb.verify())
        # only_me để ví dụ không đăng công khai — đổi thành "public" nếu muốn
        r = fb.create_post("xin chào từ fbposter 🚀", audience="only_me")
        print("post_id :", r["post_id"])
        print("permalink:", r["permalink"])
        print("dọn bài test: fb.delete_post(r[\"post_id\"])")
    except FBError as e:
        print("lỗi:", e)
    finally:
        fb.close()


if __name__ == "__main__":
    main()
