"""Liệt kê, sửa, đổi đối tượng, xoá — quản lí bài sau khi đăng."""
from fbposter import FBClient, FBError


def main() -> None:
    fb = FBClient.from_session_dir("sessions")
    try:
        posts = fb.list_posts(limit=5)
        for p in posts:
            print(p["post_id"], "|", p["time"], "|", p["text"][:50])
        if not posts:
            print("profile chưa có bài nào")
            return

        post_id = posts[0]["post_id"]

        # sửa nội dung
        fb.edit_post(post_id, text="(đã sửa)")
        print("đã sửa nội dung:", post_id)

        # đổi đối tượng xem: chỉ bạn bè
        fb.edit_post(post_id, audience="friends")
        print("privacy hiện tại:", fb.get_post_privacy(post_id))  # FRIENDS

        # xoá — bỏ comment để chạy
        # fb.delete_post(post_id)
        # print("đã xoá:", post_id)
    except FBError as e:
        print("lỗi:", e)
    finally:
        fb.close()


if __name__ == "__main__":
    main()
