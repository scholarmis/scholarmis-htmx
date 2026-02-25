import importlib
from celery import shared_task
from django.apps import apps
from django.conf import settings
from scholarmis.htmx.imports import HTMXImport
from scholarmis.framework.exports import ResourceExport, RawTableExport 
from .helpers import htmx_notify
from .message import htmx_alert_error, htmx_alert_success
from .download import send_download_link, send_download_error



@shared_task(name="tasks.import_model_resource", bind=True, ignore_result=True)     
def import_model_resource(self, user_id: str, resource_path:str, file_path: str,  action_url: str):
    """
    Process the file in chunks and import resources with progress updates.
    """
    try:
        raise_errors = getattr(settings, "IMPORT_EXPORT_SHOW_ERRORS")

        module_path, class_name = resource_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        resource_class = getattr(module, class_name)

        resource = resource_class()
        handler = HTMXImport(self, resource, file_path, user_id, action_url, raise_errors)
        
        handler.run()
    except Exception as e:
        # Handle failure
        handler.clean_up()
        context = {"error": str(e)}
        message = f"Resource Import failed: {str(e)}"
        send_download_error(user_id, context)
        htmx_notify(user_id, message)
        htmx_alert_error(user_id, message)
        

@shared_task(name="tasks.export_model_resource")
def export_model_resource(user_id: str, resource_path, export_data=True, **filters):
    try:
        module_path, class_name = resource_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        resource_class = getattr(module, class_name)
        
        exporter = ResourceExport(resource_class, export_data, **filters)
        exporter.run()
        
        file_url = exporter.get_file_url() 
  
        context = {"file_url": file_url}
        
        message = "File generated successfully"
        
        send_download_link(user_id, context)
        htmx_notify(user_id, message)
        htmx_alert_success(user_id, message)
        
    except Exception as e:
        # Handle errors by sending an error message to the UI
        context = {"error": str(e)}
        message = f"File Export failed: {str(e)}"
        send_download_error(user_id, context)
        htmx_notify(user_id, message)
        htmx_alert_error(user_id, message)
        
        
@shared_task(name="tasks.export_table_resource")
def export_table_resource(user_id, model_path, table_path, export_format, **filters):
    try:
        app_label, model_name = model_path.split('.')
        model_class = apps.get_model(app_label, model_name)
        
        module_path, class_name = table_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        
        table_class = getattr(module, class_name)
        
        exporter = RawTableExport(table_class, model_class, export_format, **filters)
        exporter.run()
        
        file_url = exporter.get_file_url() 
  
        context = {"file_url": file_url}
        
        message = "File generated successfully"
        
        send_download_link(user_id, context)
        htmx_notify(user_id, message)
        htmx_alert_success(user_id, message)
        
    except Exception as e:
        # Handle errors by sending an error message to the UI
        context = {"error": str(e)}
        message = f"File Export failed: {str(e)}"
        send_download_error(user_id, context)
        htmx_notify(user_id, message)
        htmx_alert_error(user_id, message)
        
        
        
