import os


def oauth_status(request):
    return {
        "google_oauth_configured": bool(
            os.getenv("GOOGLE_OAUTH_CLIENT_ID")
            and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        )
    }
