from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class AccountAuthenticationForm(AuthenticationForm):
    username = AuthenticationForm.base_fields["username"]
    password = AuthenticationForm.base_fields["password"]

    username.label = "아이디"
    password.label = "비밀번호"


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
