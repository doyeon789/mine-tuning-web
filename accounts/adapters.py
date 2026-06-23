from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = None
        for email_address in sociallogin.email_addresses:
            if email_address.verified and email_address.email:
                email = email_address.email
                break

        if email is None:
            email = sociallogin.user.email

        if not email:
            return

        user = (
            get_user_model()
            .objects.filter(email__iexact=email)
            .order_by("pk")
            .first()
        )
        if user is not None:
            sociallogin.connect(request, user)
