from django.views.generic import CreateView, UpdateView
from .generic import HTMXView
from .mixins import HTMXFormMixin


class HTMXFormView(HTMXView, HTMXFormMixin):
    """Base for any modal that contains a form."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context
    
    
class HTMXCreateView(HTMXFormView, CreateView):

    def get_success_url(self):
        return self.request.path
    
    
class HTMXUpdateView(HTMXFormView, UpdateView):

    def get_success_url(self):
        return self.request.path
    
