from django.http import JsonResponse, HttpResponse
from django.urls import path

def health(_request):
    return JsonResponse({"ok": True, "runtime": "django"})

def home(_request):
    return HttpResponse("<h1>Olares Django starter</h1><p>/api/health</p>")

urlpatterns = [
    path("api/health", health),
    path("", home),
]
