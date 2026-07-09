from django.contrib import admin
from django.urls import path
from apps.loans.views import sync_view, data_view, profiling_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("internal/sync/", sync_view),
    path("internal/data/", data_view),
    path("internal/profiling/", profiling_view),
]
