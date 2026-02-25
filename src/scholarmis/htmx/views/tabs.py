import re
from typing import Any, Dict, List
from django.utils.text import slugify
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import View, DetailView
from django.views.generic.detail import SingleObjectMixin
from django.shortcuts import render
from scholarmis.framework.requests import is_htmx
from .generic import HTMXView


class HTMXTabView(UserPassesTestMixin, HTMXView):
    """The interface all tabs must follow."""
    tab_name = ""
    tab_label = ""
    is_primary = False
    permission_required = None

    def test_func(self):
        if self.permission_required:
            return self.request.user.has_perm(self.permission_required)
        return True

    @classmethod
    def get_tab_metadata(cls):
        name = cls.tab_name
        label = cls.tab_label
        
        if name and not label:
            label = name.replace('_', ' ').replace('-', ' ').title()

        elif label and not name:
            name = slugify(label).replace('-', '_')

        return {
            "name": name,
            "label": label,
            "is_primary": cls.is_primary,
            "class": cls,
            "perm": cls.permission_required
        }
        
    def get_context_data(self, **kwargs):
        # Start with existing context (from HTMXView/TemplateView)
        context = super().get_context_data(**kwargs)
        # Add the tab metadata for the current active tab
        context["tab_metadata"] = self.get_tab_metadata()
        return context
        

class HTMXTemplateTabView(HTMXTabView):
    """Object-less: For general info, stats, or global settings."""
    pass


class HTMXDetailTabView(HTMXTabView, DetailView):
    """Object-ful: For specific records (requires a PK)."""
    model = None
    
   
class HTMXTabContainerView(View):
    template_name = None
    tab_classes: List[HTMXTabView] = []
    param_name = "tab"
    model = None 

    def get_parent_object(self) -> Any:
        """Fetches the primary object if the container is object-ful."""
        if not self.model:
            return None
        
        # We use a temporary mixer to leverage Django's standard lookup logic
        mixer = SingleObjectMixin()
        mixer.model = self.model
        mixer.kwargs = self.kwargs
        return mixer.get_object()

    def get_visible_tabs(self, request) -> List[Dict]:
        """Filters tab classes based on user permissions."""
        return [
            cls.get_tab_metadata() for cls in self.tab_classes 
            if not cls.permission_required or request.user.has_perm(cls.permission_required)
        ]

    def resolve_active_tab(self, request, visible_tabs: List[Dict]) -> Dict:
        """Determines active tab using URL -> Session -> Primary Flag -> Fallback."""
        session_key = f"active_tab_{self.__class__.__name__}"
        
        # 1. Check URL first
        tab_identifier = request.GET.get(self.param_name)
        
        # 2. Check Session second
        if not tab_identifier:
            tab_identifier = request.session.get(session_key)
            
        # 3. Find the requested tab
        active_tab = next((t for t in visible_tabs if t['name'] == tab_identifier), None)
        
        # 4. If nothing found, find the 'is_primary' tab, else take the first visible one
        if not active_tab:
            active_tab = next((t for t in visible_tabs if t['is_primary']), visible_tabs[0])
        
        # Update session for stickiness
        request.session[session_key] = active_tab['name']
        return active_tab

    def prepare_sub_view_context(self, request, active_tab_class, parent_object, **kwargs):
        """Instantiates the sub-view and manually resolves its object/context."""
        sub_view: HTMXTabView = active_tab_class()
        sub_view.setup(request, **kwargs)
        
        # If the tab is a DetailView, sync it with the parent or fetch its own
        if hasattr(sub_view, 'get_object'):
            sub_view.object = parent_object or sub_view.get_object()
        
        if not sub_view.test_func():
            raise PermissionDenied
            
        return sub_view.get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        visible_tabs = self.get_visible_tabs(request)
        if not visible_tabs:
            raise PermissionDenied("No authorized tabs available.")

        # Resolve state
        parent_object = self.get_parent_object()
        active_tab = self.resolve_active_tab(request, visible_tabs)
        active_class = active_tab['class']

        # 1. Handle HTMX Partial Updates
        if is_htmx(request):
            return active_class.as_view()(request, *args, **kwargs)

        # 2. Handle Full Page Load
        tab_context = self.prepare_sub_view_context(
            request, active_class, parent_object, **kwargs
        )
        
        orchestrator_context = {
            **tab_context,
            "container_object": parent_object,
            "tabs": visible_tabs,
            "active_tab": active_tab,
            "tab_param": self.param_name,
        }
        return render(request, self.template_name, orchestrator_context)