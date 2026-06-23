import os
import json
import random
from functools import lru_cache

from django.conf import settings


@lru_cache
def _load_splashes():
    splash_path = settings.BASE_DIR / "splashes.json"
    if not splash_path.exists():
        return []

    with splash_path.open(encoding="utf-8") as splash_file:
        data = json.load(splash_file)
    return data.get("splashes", [])


def oauth_status(request):
    splashes = _load_splashes()
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
        "auth_splash": random.choice(splashes) if splashes else "MINE_TUNING",
    }
