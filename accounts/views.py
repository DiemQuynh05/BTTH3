from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from candidates.models import CandidateProfile
from employers.models import EmployerProfile

from .forms import RegisterForm


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if user.role == user.Role.CANDIDATE:
            CandidateProfile.objects.create(user=user)
        else:
            EmployerProfile.objects.create(user=user, company_name=user.get_full_name() or user.username)
        login(request, user)
        messages.success(request, "Tài khoản đã được tạo thành công.")
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})
