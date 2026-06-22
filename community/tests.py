from datetime import timedelta
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import Post
from .templatetags.community_markdown import render_markdown


class MarkdownFilterTests(SimpleTestCase):
    def test_renders_heading_and_image(self):
        content = "## 설정 예시\n\n![설명](https://example.com/image.png)"

        rendered = render_markdown(content)

        self.assertIn("<h2>설정 예시</h2>", rendered)
        self.assertIn('src="https://example.com/image.png"', rendered)
        self.assertIn('alt="설명"', rendered)

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

