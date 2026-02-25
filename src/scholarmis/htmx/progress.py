from django_tenants.utils import connection
from django.template.loader import render_to_string
from scholarmis.framework.asynco.channels import channel_broadcast
from scholarmis.framework.helpers import get_template_name
from scholarmis.framework.urls import get_socket_host
from .response import htmx_render
from .message import htmx_alert_success 
from .apps import app_name


def get_task_ws_url(request, task_id):
    socket_host = get_socket_host(request)
    return f"{socket_host}/ws/tasks/{task_id}"
    

def render_task_launcher(request, task_id, message=None):
    template_name = get_template_name("task/launcher.html", app_name)
    if message:
        htmx_alert_success(request.user.id, message)
    
    task_url = get_task_ws_url(request, task_id)
    return htmx_render(request, template_name, {"task_ws_url": task_url})


def task_progress(user_id, task_id, data, tenant_schema=None):
    tenant_schema = tenant_schema or connection.schema_name
    
    channel_broadcast(
        tenant_schema=tenant_schema,
        scope="tasks",
  		method_name="task_progress", 
    	data=data,
		identifiers=[user_id, task_id]
	)
    

def send_task_progress(user_id, task_id, context, tenant_schema=None):
    template_name = get_template_name("task/progress.html", app_name)
    
    data = render_to_string(template_name, context)
    
    task_progress(user_id, task_id, data, tenant_schema)
    
    
def send_task_status(user_id, task_id, context, tenant_schema=None):
    template_name = get_template_name("task/task_status.html", app_name)
    
    data = render_to_string(template_name, context)
    
    task_progress(user_id, task_id, data, tenant_schema)
    