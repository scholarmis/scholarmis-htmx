from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from notifications.models import Notification
from scholarmis.framework.notification.helpers import get_unread_notifications
from scholarmis.framework.helpers import get_template_name 
from scholarmis.htmx.response import htmx_render, htmx_partial
from scholarmis.htmx.apps import app_name


@login_required
def mark_all_as_read(request):
    try:
        request.user.notifications.mark_all_as_read()
        
        context = {"notifications": [], "unread_count": 0}
        return htmx_render(
            request, 
            get_template_name("notify/list.html", app_name), 
            context,
            # Update the floating badge/indicator OOB
            extra_partials=[get_template_name("notify/indicator.html", app_name)]
        )
    except Exception as error:
        # Return empty response but trigger the error message OOB
        return htmx_partial(request, extra_partials=[])


@login_required
def mark_as_read(request, pk):
    try:
        notification = get_object_or_404(Notification, recipient=request.user, id=pk)
        notification.mark_as_read()
        
        unread_count = request.user.notifications.unread().count()
        context = {
            "notification": notification, 
            "unread_count": unread_count, 
            "is_htmx": True
        }
        
        return htmx_render(
            request, 
            get_template_name("notify/item.html", app_name), 
            context,
            # Sync the navbar badge automatically
            extra_partials=[get_template_name("notify/indicator.html", app_name)]
        )
    except Exception as error:
        return htmx_partial(request, extra_partials=[])


@login_required
def mark_as_unread(request, pk):
    try:
        notification = get_object_or_404(Notification, recipient=request.user, id=pk)
        notification.mark_as_unread()

        unread_count = request.user.notifications.unread().count()
        context = {
            "notification": notification, 
            "unread_count": unread_count, 
            "is_htmx": True
        }

        return htmx_render(
            request, 
            get_template_name("notify/item.html", app_name), 
            context,
            extra_partials=[get_template_name("notify/indicator.html", app_name)]
        )
    except Exception as error:
        return htmx_partial(request, extra_partials=[])


@never_cache
def notification_count(request):
    user = request.user
    # Clean check for authentication
    is_auth = user.is_authenticated
    count = user.notifications.unread().count() if is_auth else 0
    
    return htmx_render(
        request, 
        get_template_name("notify/indicator.html", app_name), 
        {"unread_count": count}
    )


@never_cache
def notification_list(request):
    user = request.user
    if not user.is_authenticated:
        return htmx_render(
            request, 
            get_template_name("notify/list.html", app_name), 
            {"notifications": []}
        )

    notifications = get_unread_notifications(user)
    unread_count = user.notifications.unread().count()

    return htmx_render(
        request, 
        get_template_name("notify/list.html", app_name), 
        {"notifications": notifications, "unread_count": unread_count}
    )