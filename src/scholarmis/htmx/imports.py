import tablib
import traceback
from scholarmis.framework.imports import ResourceImport
from scholarmis.framework.choices.process import TaskStatus
from .helpers import htmx_notify
from .message import htmx_alert_success
from .progress import send_task_progress


class HTMXImport(ResourceImport):
    
    def __init__(self, task, resource, file_path, user_id, action_url, raise_errors=True):
        super().__init__(task, resource, file_path, user_id, raise_errors)
        self.action_url = action_url


    def run(self):
        task_id = self.task.request.id
        try:
            batch_size = 500
            total_rows = len(self.dataset)

            for start in range(0, total_rows, batch_size):
                end = min(start + batch_size, total_rows)
                batch = self.dataset[start:end]

                dataset = tablib.Dataset(headers=self.headers)
                dataset.extend(batch)

                self.resource.import_data(
                    dataset=dataset, 
                    raise_errors=self.raise_errors
                )
                
                # Calculate progress
                progress = round((end / total_rows) * 100)
                message = f"Importing records. {progress}% completed."
                
                # Update Celery internal state
                self.task.update_state(state=TaskStatus.PROGRESS, meta={"progress": progress, "message": message})
                
                # Trigger WebSocket update for the UI
                send_task_progress(self.user_id, task_id, context={
                    "progress": progress,
                    "message": message,
                    "status": TaskStatus.PROGRESS
                })

            # Final Success State
            final_message = f"Process completed. Imported {total_rows} records."
            self.task.update_state(state=TaskStatus.SUCCESS, meta={"progress": 100, "message": final_message})
            
            
            send_task_progress(self.user_id, task_id, context={
                "progress": 100, 
                "message": final_message,
                "status": TaskStatus.SUCCESS,
                "action_url": self.action_url
            })
            
            htmx_notify(self.user_id, final_message)
            htmx_alert_success(self.user_id, final_message)
            
            self.clean_up()

        except Exception as e:
            error_trace = traceback.format_exc()
            message = f"Error during import: {e}"

            self.task.update_state(
                state=TaskStatus.FAILURE,
                meta={
                    "exc_type": type(e).__name__,
                    "exc_message": str(e),
                    "traceback": error_trace,
                    "message": message
                }
            )
            # Notify the UI of the failure
            send_task_progress(self.user_id, task_id, context={
                "message": message,
                "status": TaskStatus.FAILURE
            })
            self.clean_up()
