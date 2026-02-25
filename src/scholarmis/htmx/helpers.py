from .response import htmx_redirect
from .broadcast import HTMXNotify


def htmx_data_render(request, target="#htmx-data-container", swap="innerHTML"):
    return htmx_redirect(url=request.path, target=target, swap=swap)
    

def htmx_notify(users, message, **kwargs):
    """
    Send a notification to a single user via both Django Notifications and WebSockets.
    """
    return HTMXNotify.instance(users).notification(message, **kwargs)
    
