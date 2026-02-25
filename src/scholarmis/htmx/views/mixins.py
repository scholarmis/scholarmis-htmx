from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, Value
from django.db.models.functions import Concat, Coalesce
from django.http import HttpResponse
from scholarmis.framework.helpers import get_template_name
from scholarmis.framework.requests import is_htmx
from scholarmis.htmx.apps import app_name


class HTMXListMixin:
    htmx_template_base_path = "dataview"
    model = None 
    display_title = ""
    layouts = ["list", "grid"]
    default_layout = "list"
    primary_field = "id"
    title_fields = []
    display_fields = []
    resource_url = None

    def get_layout(self):
        layout = self.request.GET.get("layout") or self.request.POST.get("layout")
        if not layout: layout = self.default_layout
        clean_layout = layout.replace(".html", "")
        return clean_layout if clean_layout in self.layouts else self.default_layout

    def get_htmx_template_name(self):
        return get_template_name(f"{self.htmx_template_base_path}/{self.get_layout()}.html", app_name)

    def get_ui_context(self):
        title = self.display_title or self.model._meta.verbose_name_plural.title()
        return {
            "layout": self.get_layout(),
            "available_layouts": self.layouts,
            "primary_field": self.primary_field,
            "display_title": title,
            "resource_url": self.resource_url or "#",
            "display_config": {"title_fields": self.title_fields, "snippet_fields": self.display_fields}
        }


class HTMXSearchMixin:
    query_param = "q"
    search_fields = []
    combined_fields = []

    def get_search_query(self):
        return (self.request.POST.get(self.query_param, "").strip() or 
                self.request.GET.get(self.query_param, "").strip())

    def apply_search(self, queryset):
        query_value = self.get_search_query()
        if not query_value:
            return queryset.none()

        search_query = Q()
        fields_processed = False

        for field_group in self.combined_fields:
            fields_processed = True
            alias = "_".join(field_group) + "_combined"
            concat_args = []
            for i, field in enumerate(field_group):
                concat_args.append(Coalesce(field, Value('')))
                if i < len(field_group) - 1:
                    concat_args.append(Value(' '))
            queryset = queryset.annotate(**{alias: Concat(*concat_args)})
            search_query |= Q(**{f"{alias}__icontains": query_value})

        for field in self.search_fields:
            fields_processed = True
            search_query |= Q(**{f"{field}__icontains": query_value})

        return queryset.filter(search_query).distinct() if fields_processed else queryset.none()


class HTMXPaginationMixin:
    per_page_options = [10, 20, 50, 100]
    paginate_by = 20

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page") or self.request.POST.get("per_page")
        if per_page and str(per_page).isdigit():
            val = int(per_page)
            if val in self.per_page_options:
                return val
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context.update({
            "per_page_options": self.per_page_options,
            "current_per_page": self.get_paginate_by(None),
            "url_params": params.urlencode(),
        })
        return context


class HTMXFormMixin:
    success_url = None
    cancel_url = None
    
    def get_success_url(self):
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)

    def get_cancel_url(self):
        if not self.cancel_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a cancel_url.")
        return str(self.cancel_url)
    
    def form_valid(self, form):
        self.object = form.save()
        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "itemSaved"
            return response
        return super().form_valid(form)

    def form_invalid(self, form):
        if is_htmx(self.request):
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)
    

class HTMXModalMixin:
    modal_title = ""
    modal_size = "max-w-2xl"
    modal_icon = "fas fa-edit"
    show_save_button = True
    save_button_text = "Save Changes"
    cancel_button_text = "Cancel"

    def get_modal_title(self):
        if self.modal_title: return self.modal_title
        verb = "View"
        if hasattr(self, 'object') and self.object:
            verb = "Update"
        return f"{verb} {self.model._meta.verbose_name.title()}"

    def get_modal_config(self):
        return {
            "title": self.get_modal_title(),
            "size": self.modal_size,
            "icon": self.modal_icon,
            "show_save": self.show_save_button,
            "save_text": self.save_button_text,
            "cancel_text": self.cancel_button_text,
        }

