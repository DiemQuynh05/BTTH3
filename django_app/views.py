from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok", "service": "He_Thong_Tim_Viec"})
