import inspect
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django_tables2 import LazyPaginator
from django_tables2.views import SingleTableMixin
from django_tables2.export import ExportMixin
from django_filters.views import FilterView
from scholarmis.framework.requests import is_htmx
from scholarmis.framework.helpers import get_template_name
from scholarmis.htmx.actions import BulkAction, RowAction
from scholarmis.htmx.download import render_download_launcher
from scholarmis.htmx.tasks import export_table_resource, export_model_resource
from scholarmis.htmx.apps import app_name


class HTMXTableView(SingleTableMixin, FilterView):
    htmx_template_name = get_template_name("table/table.html", app_name)
    paginator_class = LazyPaginator
    per_page_options = [10, 20, 50, 100]
    table_pagination = {"per_page": 20}
    show_filters = True
 
    bulk_actions: list[BulkAction] = []
    
    row_actions: list[RowAction] = []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bulk_actions = [
            a() if inspect.isclass(a) else a for a in self.bulk_actions
        ]
        self.row_actions = [
            a() if inspect.isclass(a) else a for a in self.row_actions
        ]
        
    def get_htmx_template_name(self):
        """
        Returns the htmx_template_name defined on the class or subclass.
        """
        return self.htmx_template_name
    
    def get_table(self, **kwargs):
        table = super().get_table(**kwargs)
        table.row_actions = self.row_actions
        table.request = self.request
        table.view = self
        return table
    
    def handle_row_action(self, name, record_id):
        action = next((a for a in self.row_actions if a.name == name), None)
        if not action or not action.is_htmx:
            return HttpResponseBadRequest()

        record = self.get_queryset().filter(pk=record_id).first()
        if not record:
            return HttpResponseNotFound()

        if not action.is_allowed(self.request, record):
            return HttpResponseForbidden()

        return action.handle(self.request, record)
    
    def handle_bulk_action(self, name, row_ids):

        action_obj = next((a for a in self.bulk_actions if a.name == name), None)
        
        if action_obj:
            return action_obj.handle(self, self.request, row_ids)          
    
    def post(self, request, *args, **kwargs):
        bulk_action = request.POST.get("bulk_action")
        selected_ids = request.POST.getlist("selected_ids")
        
        htmx_action = request.POST.get("htmx_action")
        record_id = request.POST.get("record_id")

        if bulk_action:
           return self.handle_bulk_action(bulk_action, selected_ids)
            
        elif htmx_action and record_id : 
           return self.handle_row_action(htmx_action, record_id)
                
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "per_page_options": self.per_page_options,
            "bulk_actions": self.bulk_actions, 
            "show_filters": self.show_filters, 
        })
        return context

    def get_template_names(self):
        if is_htmx(self.request):
            template_name = self.get_htmx_template_name()
            return [template_name]
        return [self.template_name]
  
 
class HTMXExportableTableView(ExportMixin, HTMXTableView):
    resource_class = None
    model = None
    export_formats = ["xlsx"]
    export_trigger_param = "_export"  # Ensure this matches your template trigger

    def get_filters(self):
        """
        Extracts valid filter data from the filterset. 
        Converts model instances to PKs so they are JSON serializable for Celery.
        """
        if hasattr(self, 'filterset') and self.filterset.form.is_valid():
            data = self.filterset.form.cleaned_data
            return {
                k: (v.pk if hasattr(v, 'pk') else v) 
                for k, v in data.items() 
                if v not in [None, '', [], (), {}]
            }
        return {}

    def get_path(self, obj):
        """
        Helper to get the full python dot-path of a class.
        """
        if not obj:
            return None
        return f"{obj.__module__}.{obj.__name__}"

    def export_table(self, export_format):
        """
        Triggers a task to export data based on the django-tables2 definition.
        """
        user_id = self.request.user.id
        # Use _meta for robust model path resolution
        model_path = f"{self.model._meta.app_label}.{self.model.__name__}"
        table_path = self.get_path(self.table_class)
        
        filters = self.get_filters()
        
        export_table_resource.delay(
            user_id, model_path, table_path, export_format, **filters
        )
    
    def export_resource(self):
        """
        Triggers a task to export data based on a django-import-export Resource.
        """
        user_id = self.request.user.id
        resource_path = self.get_path(self.resource_class)
        
        filters = self.get_filters()
        
        export_model_resource.delay(
            user_id, resource_path, export_data=True, **filters
        )

    def render_to_response(self, context, **kwargs):
        """
        Intercepts the render process to catch HTMX export requests 
        before the full table renders.
        """
        # 1. Detect Export Trigger (HTMX + POST is the safest way to trigger tasks)
        if self.request.method == "POST" and is_htmx(self.request):
            export_format = self.request.GET.get(self.export_trigger_param)
            
            if export_format in self.export_formats:
                if self.resource_class:
                    self.export_resource()
                else:
                    self.export_table(export_format)
                
                # 2. Return the 'Launcher' which likely contains the polling UI/Progress bar
                return render_download_launcher(self.request, context)

        # 3. Default behavior: Render the table page as usual
        return super().render_to_response(context, **kwargs)

