"""
URL configuration for nail_salon_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("dashboard.urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.services.urls")),
    path("", include("apps.appointments.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.profiles.urls")),
    path("", include("apps.tareas.urls")),
]

# Servir archivos de media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "apps.common.views.error_views.bad_request"
handler403 = "apps.common.views.error_views.permission_denied"
handler404 = "apps.common.views.error_views.page_not_found"
handler500 = "apps.common.views.error_views.server_error"
