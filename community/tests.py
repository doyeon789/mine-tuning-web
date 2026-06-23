from datetime import timedelta
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Post
from .templatetags.community_markdown import render_markdown
from .views import _popular_posts


class MarkdownFilterTests(SimpleTestCase):
    def test_renders_heading_and_image(self):
        content = "## 설정 예시\n\n![설명](https://example.com/image.png)"

        rendered = render_markdown(content)

        self.assertIn("<h2>설정 예시</h2>", rendered)
        self.assertIn('src="https://example.com/image.png"', rendered)
        self.assertIn('alt="설명"', rendered)

    def test_renders_uploaded_media_image(self):
        rendered = render_markdown(
            "![로컬 이미지](/media/community/markdown/sample.png)"
        )

        self.assertIn(
            'src="/media/community/markdown/sample.png"',
            rendered,
        )
    def test_removes_unsafe_html_and_protocols(self):
        content = '<script>alert("xss")</script>\n\n[위험](javascript:alert(1))'

        rendered = render_markdown(content)

        self.assertNotIn("<script", rendered)
        self.assertNotIn("javascript:", rendered)


class CommunityMarkdownViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="writer",
            password="test-password",
        )
        self.post = Post.objects.create(
            author=self.user,
            title="마크다운 글",
            content="## 제목\n\n![이미지](https://example.com/image.png)",
        )
        self.client.force_login(self.user)

    def test_post_detail_renders_markdown_without_cdn(self):
        response = self.client.get(
            reverse("community:post_detail", kwargs={"pk": self.post.pk})
        )

        self.assertContains(response, "<h2>제목</h2>", html=True)
        self.assertContains(response, "https://example.com/image.png")
        self.assertNotContains(response, "cdn.jsdelivr.net")
        self.assertNotContains(response, "post.image")
    def test_post_form_loads_markdown_image_editor(self):
        response = self.client.get(reverse("community:post_create"))

        self.assertContains(response, "data-markdown-editor")
        self.assertContains(response, "js/community_markdown.js")
        self.assertContains(
            response,
            reverse("community:markdown_image_upload"),
        )
    def test_create_post_with_markdown_content(self):
        response = self.client.post(
            reverse("community:post_create"),
            {
                "title": "새 마크다운 글",
                "content": "## 생성 성공\n\n![이미지](https://example.com/new.png)",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h2>생성 성공</h2>", html=True)
        self.assertContains(response, "https://example.com/new.png")

class PostMetadataTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="metadata-writer",
            password="test-password",
        )
        self.post = Post.objects.create(
            author=self.user,
            title="메타정보 글",
            content="본문",
        )
        self.client.force_login(self.user)

    def test_new_post_does_not_show_edited_badge(self):
        response = self.client.get(
            reverse("community:post_detail", kwargs={"pk": self.post.pk})
        )

        self.assertFalse(self.post.is_edited)
        self.assertNotContains(response, "수정됨")

    def test_updated_post_shows_edited_badge(self):
        edited_at = self.post.created_at + timedelta(seconds=2)
        Post.objects.filter(pk=self.post.pk).update(updated_at=edited_at)
        self.post.refresh_from_db()

        response = self.client.get(
            reverse("community:post_detail", kwargs={"pk": self.post.pk})
        )

        self.assertTrue(self.post.is_edited)
        self.assertContains(response, "수정됨")


class PopularPostQueryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="popular-writer",
            password="test-password",
        )
        self.liker1 = get_user_model().objects.create_user(username="liker1")
        self.liker2 = get_user_model().objects.create_user(username="liker2")

    def create_post(self, title, view_count, created_at, liked_users=None):
        post = Post.objects.create(
            author=self.user,
            title=title,
            content="본문",
            view_count=view_count,
        )
        if liked_users:
            post.liked_users.add(*liked_users)
        Post.objects.filter(pk=post.pk).update(created_at=created_at)
        return post

    def test_orders_by_score_likes_and_newer_created_at(self):
        now = timezone.now()
        older_same_score = self.create_post(
            "동점 오래된 글",
            8,
            now - timedelta(hours=3),
            [self.liker1],
        )
        higher_likes = self.create_post(
            "동점 좋아요 많은 글",
            7,
            now - timedelta(hours=4),
            [self.liker1, self.liker2],
        )
        newer_same_likes = self.create_post(
            "동점 최신 글",
            8,
            now - timedelta(hours=1),
            [self.liker1],
        )
        highest_score = self.create_post(
            "점수 높은 글",
            20,
            now - timedelta(hours=2),
        )

        posts = list(_popular_posts("realtime"))

        self.assertEqual(
            posts,
            [
                highest_score,
                higher_likes,
                newer_same_likes,
                older_same_score,
            ],
        )

    def test_filters_by_selected_period(self):
        now = timezone.now()
        recent_post = self.create_post(
            "최근 글",
            1,
            now - timedelta(hours=2),
        )
        self.create_post(
            "하루 지난 글",
            100,
            now - timedelta(days=2),
        )

        self.assertEqual(list(_popular_posts("realtime")), [recent_post])
        self.assertEqual(len(list(_popular_posts("weekly"))), 2)


class PopularPostListViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="popular-list-writer",
            password="test-password",
        )

    def test_popular_page_uses_selected_period(self):
        now = timezone.now()
        recent_post = Post.objects.create(
            author=self.user,
            title="실시간 인기글",
            content="본문",
            view_count=10,
        )
        old_post = Post.objects.create(
            author=self.user,
            title="오래된 인기글",
            content="본문",
            view_count=100,
        )
        Post.objects.filter(pk=recent_post.pk).update(
            created_at=now - timedelta(hours=1)
        )
        Post.objects.filter(pk=old_post.pk).update(
            created_at=now - timedelta(days=2)
        )

        response = self.client.get(
            reverse("community:popular_post_list") + "?period=realtime"
        )

        self.assertContains(response, "인기 게시글")
        self.assertContains(response, "실시간 인기글")
        self.assertNotContains(response, "오래된 인기글")


class MarkdownImageUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="image-writer",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

    def test_uploads_valid_image_and_returns_media_url(self):
        image = SimpleUploadedFile(
            "sample.png",
            b"\x89PNG\r\n\x1a\n" + b"image-data",
            content_type="image/png",
        )

        response = self.client.post(
            reverse("community:markdown_image_upload"),
            {"image": image},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["url"].startswith("/media/community/"))

    def test_rejects_file_with_invalid_image_signature(self):
        image = SimpleUploadedFile(
            "fake.png",
            b"<html>not an image</html>",
            content_type="image/png",
        )

        response = self.client.post(
            reverse("community:markdown_image_upload"),
            {"image": image},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "올바른 이미지 파일이 아닙니다.")

    def test_requires_login(self):
        self.client.logout()

        response = self.client.post(
            reverse("community:markdown_image_upload"),
            {
                "image": SimpleUploadedFile(
                    "sample.png",
                    b"\x89PNG\r\n\x1a\n" + b"image-data",
                    content_type="image/png",
                )
            },
        )

        self.assertEqual(response.status_code, 302)



