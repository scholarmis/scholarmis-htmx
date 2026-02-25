from django.template.loader import render_to_string
from scholarmis.framework.asynco.broadcast import user_broadcast
from scholarmis.framework.helpers import get_template_name
from .apps import app_name


class HTMXMessage:
    text = None
    tags = None
    
    
    def __init__(self, text, tags=None):
        self.text = text
        self.tags = tags
        
        
    def __str__(self):
        return self.text


def get_message_template():
    return get_template_name("message/message.html", app_name)


def htmx_alert_message(user_id, text, tags):
    template_name = get_message_template()
    message = HTMXMessage(text, tags)
    
    data = render_to_string(template_name, {
        "messages": [message]
    })
  
    user_broadcast(user_id, data)
    

def htmx_alert_success(user_id, text):
    htmx_alert_message(user_id, text, "success")


def htmx_alert_error(user_id, text):
    htmx_alert_message(user_id, text, "error")


def htmx_alert_warning(user_id, text):
    htmx_alert_message(user_id, text, "warning")


def htmx_alert_info(user_id, text):
    htmx_alert_message(user_id, text, "info")

