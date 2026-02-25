from django.views.generic import View, DetailView, FormView
from django.views.generic.base import TemplateResponseMixin
from django_filters.views import FilterView
from django.shortcuts import redirect
from scholarmis.framework.forms.imports import ImportExcelForm
from scholarmis.framework.requests import is_htmx
from scholarmis.framework.files.utils import save_uploaded_file
from scholarmis.framework.feedback import get_import_feedback
from scholarmis.htmx.progress import render_task_launcher
from scholarmis.htmx.response import htmx_redirect
from scholarmis.htmx.tasks import import_model_resource, export_model_resource
from scholarmis.htmx.response import htmx_render
from scholarmis.htmx.message import htmx_alert_success, htmx_alert_error
from .mixins import HTMXFormMixin, HTMXListMixin, HTMXPaginationMixin, HTMXSearchMixin


class HTMXView(TemplateResponseMixin, View):
    htmx_template_name = None 

    def get_template_names(self):
        if is_htmx(self.request):
            return [self.htmx_template_name]
        return [self.template_name]

    def render_to_response(self, context, **response_kwargs):
        if is_htmx(self.request):
            return htmx_render(self.request, self.htmx_template_name, context)
        return super().render_to_response(context, **response_kwargs)
    
    def alert_success(self, text):
        return htmx_alert_success(self.request.user.id, text)
    
    def alert_error(self, text):
        return htmx_alert_error(self.request.user.id, text)


class HTMXListView(HTMXListMixin, HTMXPaginationMixin, FilterView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["results"] = context.get("object_list")
        context.update(self.get_ui_context())
        return context

    def render_to_response(self, context, **response_kwargs):
        if is_htmx(self.request):
            return htmx_render(self.request, self.get_htmx_template_name(), context)
        return super().render_to_response(context, **response_kwargs)


class HTMXSearchView(HTMXSearchMixin, HTMXListView):
    htmx_template_base_path = "search"
    
    def get_queryset(self):
        return self.apply_search(super().get_queryset())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.get_search_query()
        context.update({"query": query, "has_query": bool(query)})
        return context
    
    
class HTMXDetailView(DetailView, HTMXView):
    pass


class HTMXImportView(HTMXFormMixin, FormView):
    htmx_file_target = "#htmx-download"
    export_trigger_param = "_export"
    form_class = ImportExcelForm
    resource_class = None  # Expected to be a django-import-export Resource class

    def get(self, request, *args, **kwargs):
        """
        Intercepts GET requests to check for export triggers (e.g., downloading a template).
        """
        # Ensure this matches the attribute name defined at the class level
        export = request.GET.get(self.export_trigger_param)
        
        if export == "template":
            # This triggers the Celery task defined in your export_resource method
            self.export_resource()
        
            # Use htmx_redirect to refresh the page or move to a 'Task Pending' view
            # If this isn't an HTMX request, a standard redirect should be used as fallback
            if is_htmx(request):
                return htmx_redirect(request.path, target=self.htmx_file_target)
            return redirect(request.path)
            
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """
        Injects the resolved cancel_url into the template context.
        """
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_cancel_url() 
        context["export_trigger_param"] = self.export_trigger_param
        return context

    def get_resource_path(self):
        """
        Helper to return the full python path of the resource class for background tasks.
        """
        if not self.resource_class:
            raise AttributeError(f"{self.__class__.__name__} requires 'resource_class' to be defined.")
        return f"{self.resource_class.__module__}.{self.resource_class.__name__}"

    def import_resource(self, file_path, action_url):
        """
        Triggers the asynchronous import task.
        """
        user_id = self.request.user.id
        resource_path = self.get_resource_path()
        # Ensure your task is set up to handle these specific arguments
        return import_model_resource.delay(user_id, resource_path, file_path, action_url)
    
    def export_resource(self):
        """
        Triggers the asynchronous export task or returns a download response.
        """
        user_id = self.request.user.id
        resource_path = self.get_resource_path()
        export_data = False
        
        # Initialize filters as empty dict to allow unpacking (**filters) safely
        filters = {} 
        
        export_model_resource.delay(user_id, resource_path, export_data, **filters)
        
        # For HTMX, you might want to return a notification that the export has started
        # Or redirect back to the current page.
        return self.render_to_response(self.get_context_data())
        
    def form_valid(self, form):
        """
        Handles the file upload, saves it temporarily, and starts the import task.
        """
        file = form.cleaned_data["file"]
        
        # Save file to a temporary location accessible by the celery worker
        file_path = save_uploaded_file(self.request, file)
        
        # Get the resolved success URL to redirect the user after the task completes
        success_url = self.get_success_url()

        # Trigger the task logic
        task = self.import_resource(file_path, success_url)
        
        # Provide UI feedback (e.g., progress bar or 'Processing...' message)
        feedback = get_import_feedback()
        
        return render_task_launcher(self.request, task.id, feedback)
    