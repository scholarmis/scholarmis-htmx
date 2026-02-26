from django.template.loader import render_to_string
from notifications.models import Notification
from scholarmis.framework.asynco.broadcast import Broadcast
from scholarmis.framework.notification.notify import Notify
from scholarmis.framework.helpers import get_template_name
from .apps import app_name


class HTMXNotify(Notify):
    """
    Extends Notify to render HTML fragments for HTMX clients.
    Allows passing a specific template for different UI contexts.
    """
    
    def __init__(self, users, tenant_schema=None, template=None):
        super().__init__(users, tenant_schema)
        self.notification_template = template or get_template_name("notify/websocket.html",app_name)

    def broadcast(self, user, notification: Notification):
        
        unread_count = user.notifications.unread().count()
        
        payload = render_to_string(self.notification_template, {
            "notification": notification,
            "unread_count": unread_count,
        })

        broadcast = Broadcast(self.tenant_schema)
        broadcast.to_user( 
            user_id=user.id, 
            data=payload 
        )
        
    @staticmethod
    def instance(users, tenant_schema=None):
        """
        Static method to instantiate the Notify class with the provided users.

        :param users: A single User instance or a list of User instances.
        :return: An instance of Notify.
        """
        return HTMXNotify(users, tenant_schema)
