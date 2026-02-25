from django.urls import path
from scholarmis.htmx.apps import app_name
from . import views


app_name = app_name

urlpatterns = [
    path("mark-as-read/<int:pk>", views.mark_as_read, name="mark_as_read"),
    path("mark-as-unread/<int:pk>", views.mark_as_unread, name="mark_as_unread"),
    path("mark-all-as-read", views.mark_all_as_read, name="mark_all_as_read"),
    path("htmx-notification-list", views.notification_list, name="notification_list"),
    path("notification-count", views.notification_count, name="notification_count"),
]