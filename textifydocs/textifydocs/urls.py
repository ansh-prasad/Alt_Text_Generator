from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect  # Import redirect function

def redirect_to_upload(request):
    return redirect("/file/upload/")  # Redirect from "/" to "/file/upload/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("file/", include("file_processor.urls")),
    path("", redirect_to_upload),  # Redirect root URL to upload page
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
