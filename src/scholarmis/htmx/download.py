from django.template.loader import render_to_string
from scholarmis.framework.helpers import get_template_name
from scholarmis.framework.asynco.broadcast import user_broadcast
from .response import htmx_render
from .apps import app_name


def render_download_launcher(request, context=None):
    template_name = get_template_name("download/launcher.html", app_name)
    return htmx_render(request, template_name, context)


def send_download_link(user_id, context):
    template_name = get_template_name("download/link.html", app_name)
    data = render_to_string(template_name, context)
    user_broadcast(user_id, data)
    

def send_download_error(user_id, context):
    template_name = get_template_name("download/error.html", app_name)
    data = render_to_string(template_name, context)
    user_broadcast(user_id, data)
     