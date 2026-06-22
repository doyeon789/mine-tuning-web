from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
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
