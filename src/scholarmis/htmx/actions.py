import json
from typing import Any, List, Optional
from .message import htmx_alert_success
from .helpers import htmx_data_render


class BaseAction:
    """Unified metadata for all actions."""
    name: str
    label: Optional[str] = None
    icon: Optional[str] = None
    confirm: Optional[str] = None
    order: int = 1
    perms: List[str] = []
    visible: bool = True
    open_tab: bool =  False
    is_danger: bool = False
    is_primary: bool = False

    def is_allowed(self, request, record) -> bool:
        user = request.user
        if not self.visible: return False
        if self.perms and not user.has_perms(self.perms): return False
        return True
    
    def can_confirm(self):
        return True if self.confirm else False

    def get_label(self):
        return self.label or self.name.replace("_", " ").title()

    def serialize(self, request=None, record=None, view=None) -> dict:
        return {
            "name": self.name,
            "label": self.get_label(),
            "icon": self.icon,
            "confirm": self.confirm,
            "can_confirm": self.can_confirm(),
            "open_tab": self.open_tab,
            "is_danger": self.is_danger,
            "is_primary": self.is_primary,
            "order": self.order,
        }


class RowAction(BaseAction):
    """Base for row-level interactions."""
    def handle(self, request, record):
        """Override for logic-heavy or modal-returning actions."""
        return None


class LinkAction(RowAction):
    """Standard <a href> link for page navigation."""
    
    def get_url(self, request, record): 
        raise NotImplementedError()

    def serialize(self, request=None, record=None, view=None):
        data = super().serialize(request, record, view)
        data["url"] = self.get_url(request, record)
        return data


class HtmxAction(RowAction):
    """Base for any action that swaps content."""
    htmx_target = "#htmx-data-container"
    htmx_loader = "#htmx-data-loader"
    htmx_swap = "innerHTML"
    is_htmx = True
    method = "GET"

    def get_url(self, request, record): 
        return None
    
    def get_payload(self, request, record):
        """Standard payload logic."""
        return {
            "htmx_action": self.name,
            "record_id": str(getattr(record, "pk", "")),
        }

    def serialize(self, request=None, record=None, view=None):
        data = super().serialize(request, record, view)
        data.update({
            "is_htmx": self.is_htmx,
            "hx_method": self.method.upper(),
            "hx_url": self.get_url(request, record) or request.path,
            "hx_target": self.htmx_target,
            "hx_indicator": self.htmx_loader,
            "hx_confirm": self.confirm,
            "payload": self.get_payload(request, record), # Use the method here
        })
        return data


class ModalAction(HtmxAction):
    """Opens the global modal shell."""
    htmx_target = "#htmx-modal"
    method = "GET"
    
    def get_payload(self, request, record):
        """Override to return an empty payload."""
        return {}
    

class ServerAction(HtmxAction):
    """Performs server logic (POST) and refreshes the ui."""
    target = "#htmx-data-container"
    method = "POST"
    confirm = "Are you sure you want to perform this action ?"


class BulkAction(BaseAction):
    """Actions performed on multiple selected rows."""
    confirm = "Perform this action on selected items ?"
    htmx_swap = "innerHTML"
    htmx_target = None
   
    def handle(self, view, request, row_ids: List[Any]):
        raise NotImplementedError()

    def serialize(self, request=None, record=None, view=None):
        data = super().serialize(request, record, view)
        data.update({
            "is_bulk": True,
            "hx_post": request.path if request else "",
            "hx_confirm": self.confirm,
            "payload": {"bulk_action": self.name}
        })
        return data
    
    
class DeleteTableRows(BulkAction):
    name = "delete_selected"
    label = "Delete Selected"
    icon = "fas fa-trash"
    order = 99
    is_danger = True 
    
    def handle(self, view, request, row_ids: List[Any]):
        queryset = view.get_queryset().filter(pk__in=row_ids)
        count = queryset.count()
        queryset.delete()

        htmx_alert_success(request.user.id, f"Successfully deleted {count} rows.")
        return htmx_data_render(request)
 
   
class ActionMenu:
    """
    Helper to convert a list of RowAction instances to JSON for frontend.
    """
    def __init__(self, actions: List[RowAction]):
        self.actions = actions

    def get_json(self) -> str:
        return json.dumps(self.actions)

    def __str__(self):
        return self.get_json()

