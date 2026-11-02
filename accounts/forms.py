from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=[(User.Role.CANDIDATE, "Ứng viên"), (User.Role.EMPLOYER, "Nhà tuyển dụng")])

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "password1", "password2")


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Tên đăng nhập")
