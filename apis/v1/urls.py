from django.urls import path

from apis.v1.docs.view import DocsView, SchemaView
from apis.v1.startup.view import StartupView

urlpatterns = [
    path("startup/", StartupView.as_view(), name="api_startup"),
    path("schema/", SchemaView.as_view(), name="api_schema"),
    path("docs/", DocsView.as_view(), name="api_docs"),
]
