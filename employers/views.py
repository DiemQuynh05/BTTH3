from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import EmployerProfileForm
from .models import EmployerProfile


@login_required
def profile(request):
    if request.user.role != request.user.Role.EMPLOYER:
        return render(request, "errors/403.html", status=403)
    employer, _ = EmployerProfile.objects.get_or_create(user=request.user, defaults={"company_name": request.user.username})
    form = EmployerProfileForm(request.POST or None, request.FILES or None, instance=employer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thông tin doanh nghiệp đã được cập nhật.")
        return redirect("employer-profile")
    return render(request, "employers/profile.html", {"form": form, "employer": employer})
