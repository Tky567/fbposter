"""Vòng đời hoàn toàn trên bài của chính ví dụ — không đụng bài thật.

Tạo bài only_me → sửa nội dung → đổi nhãn AI → đọc privacy → xoá.
"""
from fbposter import FBClient, FBError


def main() -> None:
    fb = FBClient.from_session_dir("sessions")
    try:
        print(fb.verify())

        # tạo bài riêng only_me để thao tác
        r = fb.create_post("bài test của ví dụ manage_posts",
                           audience="only_me")
        print("tạo:", r["post_id"], "| privacy:",
              fb.get_post_privacy(r["post_id"]))

        # sửa nội dung + gắn nhãn AI
        fb.edit_post(r["post_id"], text="(đã sửa trong ví dụ)")
        fb.edit_post(r["post_id"], ai_generated=True)
        print("đã sửa bài test")

        # xoá dọn
        print("xoá:", fb.delete_post(r["post_id"]))
    except FBError as e:
        print("lỗi:", e)
    finally:
        fb.close()


if __name__ == "__main__":
    main()
