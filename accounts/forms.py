from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class AccountAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "아이디 또는 비밀번호가 올바르지 않습니다. 다시 확인해 주세요.",
        "inactive": "이 계정은 현재 사용할 수 없습니다.",
    }

    username = AuthenticationForm.base_fields["username"]
    password = AuthenticationForm.base_fields["password"]

    username.label = "아이디"
    password.label = "비밀번호"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "username",
                "placeholder": "아이디",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "placeholder": "비밀번호",
            }
        )


class AccountCreationForm(UserCreationForm):
    error_messages = {
        **UserCreationForm.error_messages,
        "password_mismatch": "비밀번호 확인이 일치하지 않습니다.",
    }

    class Meta(UserCreationForm.Meta):
        labels = {
            "username": "아이디",
        }
        error_messages = {
            "username": {
                "unique": "이미 사용 중인 아이디입니다.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "아이디"
        self.fields["password1"].label = "비밀번호"
        self.fields["password2"].label = "비밀번호 확인"
