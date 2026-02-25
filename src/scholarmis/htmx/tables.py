import django_tables2 as tables
from scholarmis.framework.helpers import get_template_name
from scholarmis.framework.tables.columns import CustomCheckBoxColumn
from .actions import  RowAction, ActionMenu
from .apps import app_name


class TaskStatusColumn(tables.TemplateColumn):
    column_template_name = get_template_name("table/columns/task_status.html", app_name)
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template_name", self.column_template_name)
        kwargs.setdefault("orderable", False)
        kwargs.setdefault("verbose_name", "Task status")
        super().__init__(*args, **kwargs)


class BaseTable(tables.Table):
    selection = CustomCheckBoxColumn(
        accessor="pk", 
        exclude_from_export=True,
        orderable=False
    )
    
    class Meta:
        abstract = True
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.get("request")
        super().__init__(*args, **kwargs)

        self.row_attrs = {
            "data-row-id": lambda record: f"{record.pk}",
            "data-row-actions": lambda record: self.get_row_menu(record),
        }
        
    def get_row_menu(self, record):
        request = getattr(self, "request", None)
        view = getattr(self, "view", None)
        
        # 1. Get the raw action objects
        raw_actions: list[RowAction] = getattr(view, "row_actions", [])

        # 2. Filter, Serialize, and Sort
        # We sort by the "order" attribute. We use getattr(action, "order", 99) 
        actions = [
            action.serialize(request, record, view)
            for action in sorted(
                [a for a in raw_actions if a.is_allowed(request, record)],
                key=lambda x: getattr(x, "order", 99)
            )
        ]
        
        return ActionMenu(actions)


class TaskTable(BaseTable):
    
    task_status = TaskStatusColumn()
    
    class Meta:
        abstract = True
    