
from scholarmis.framework.urls import get_socket_host

def htmx_ws_url(request):
    socket_host = get_socket_host(request)
    return {
        "htmx_ws_url": f"{socket_host}/ws/htmx/"
    }



