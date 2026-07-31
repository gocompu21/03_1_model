from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text="이메일 주소를 입력해주세요.",
    )

    first_name = forms.CharField(
        max_length=30, required=True, help_text="이름을 입력해주세요.", label="이름"
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("사용자 이름이 이미 있습니다.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("이메일이 이미 있습니다.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        """승인 대기 중이면 그 사실을 알려준다.

        기본 ModelBackend는 비활성 사용자를 인증 단계에서 거절하므로
        confirm_login_allowed까지 가지 않는다. 그래서 인증 실패 시
        아이디/비밀번호가 맞는데 비활성인 경우인지 직접 확인한다.
        """
        try:
            return super().clean()
        except forms.ValidationError:
            username = self.cleaned_data.get("username")
            password = self.data.get("password")
            user = User.objects.filter(username=username).first()

            if user and not user.is_active and password and user.check_password(password):
                approval = getattr(user, "signup_approval", None)
                if approval and approval.status == "pending":
                    raise forms.ValidationError(
                        "가입 승인 대기 중입니다. 관리자 승인 후 로그인할 수 있습니다.",
                        code="pending_approval",
                    )
                raise forms.ValidationError(
                    "사용할 수 없는 계정입니다. 관리자에게 문의해 주세요.",
                    code="inactive",
                )
            raise
