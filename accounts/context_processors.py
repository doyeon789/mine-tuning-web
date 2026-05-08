import os


def oauth_status(request):
    oauth_providers = [
        {
            "id": "google",
            "label": "Google",
            "configured": bool(
                os.getenv("GOOGLE_OAUTH_CLIENT_ID")
                and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
            ),
        },
        {
            "id": "kakao",
            "label": "Kakao",
            "configured": bool(os.getenv("KAKAO_OAUTH_CLIENT_ID")),
        },
        {
            "id": "naver",
            "label": "Naver",
            "configured": bool(
                os.getenv("NAVER_OAUTH_CLIENT_ID")
                and os.getenv("NAVER_OAUTH_CLIENT_SECRET")
            ),
        },
    ]

    return {
        "oauth_providers": oauth_providers,
        "any_oauth_configured": any(provider["configured"] for provider in oauth_providers),
    }
