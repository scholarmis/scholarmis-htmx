from django.http import HttpResponse
from django.views.generic import CreateView, UpdateView, DeleteView
from scholarmis.framework.helpers import get_template_name
from scholarmis.framework.requests import is_htmx
from scholarmis.htmx.response import htmx_render
from scholarmis.htmx.apps import app_name
from .generic import HTMXView
from .mixins import HTMXFormMixin, HTMXModalMixin


class HTMXModal(HTMXModalMixin, HTMXView):
    htmx_template_name = get_template_name("modal/modal.html", app_name)
    modal_template_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.modal_template_name:
            raise ValueError(f"{self.__class__.__name__} requires modal_template_name.")
        context["modal_template_name"] = self.modal_template_name
        context["modal"] = self.get_modal_config()
        return context

    def render_to_response(self, context, **response_kwargs):
        return htmx_render(self.request, self.htmx_template_name, context)
     

class HTMXFormModal(HTMXModal, HTMXFormMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context: 
            context['form'] = self.get_form()
        return context


class HTMXCreateModal(HTMXFormModal, CreateView):
    def get_success_url(self): 
        return self.request.path


class HTMXUpdateModal(HTMXFormModal, UpdateView):
    def get_success_url(self): 
        return self.request.path


class HTMXDeleteModal(HTMXModal, DeleteView):
    modal_title = "Confirm Deletion"
    save_button_text = "Yes, Delete"
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "itemSaved"
            return response
        return super().delete(request, *args, **kwargs)

