from django.views import View
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse


class WizardStep:
    key = None
    label = None
    template_name = None
    form_class = None
    optional = False

    def get_form(self, **kwargs):
        return self.form_class(**kwargs)

    def can_enter(self, session):
        return True

    def can_exit(self, session, form):
        return form.is_valid()

    def on_enter(self, session):
        pass

    def on_exit(self, session, form):
        pass


class WizardWorkflow:
    key = None
    steps = []

    def get_step(self, key):
        for step in self.steps:
            if step.key == key:
                return step
        raise KeyError(f"Unknown step: {key}")

    def first_step(self):
        return self.steps[0].key

    def step_keys(self):
        return [s.key for s in self.steps]

    def next_step(self, current_key):
        keys = self.step_keys()
        idx = keys.index(current_key)
        return keys[idx + 1] if idx < len(keys) - 1 else None

    def previous_step(self, current_key):
        keys = self.step_keys()
        idx = keys.index(current_key)
        return keys[idx - 1] if idx > 0 else None


class WizardSession:
    def __init__(self, request, workflow):
        self.request = request
        self.key = f"wizard:{workflow.key}"
        self.state = request.session.setdefault(
            self.key,
            {"current": None, "completed": [], "data": {}}
        )

    @property
    def current(self):
        return self.state["current"]

    @property
    def completed(self):
        return self.state["completed"]

    @property
    def data(self):
        return self.state["data"]

    def start(self, first_step):
        if not self.current:
            self.state["current"] = first_step
            self.request.session.modified = True

    def complete_step(self, step_key, data):
        self.state["data"][step_key] = data
        if step_key not in self.completed:
            self.completed.append(step_key)
        self.request.session.modified = True

    def go_to(self, step_key):
        self.state["current"] = step_key
        self.request.session.modified = True

    def reset(self):
        self.request.session.pop(self.key, None)
        self.request.session.modified = True


class BaseWizardView(View):
    workflow_class = None

    # ---------- SETUP ----------

    def setup_wizard(self, request, **kwargs):
        self.request = request
        self.workflow = self.workflow_class()
        self.session = WizardSession(request, self.workflow)

        self.session.start(self.workflow.first_step())

        self.step_key = kwargs["step_key"]
        self.step = self.workflow.get_step(self.step_key)

    # ---------- ACCESS GUARD ----------

    def can_access_step(self):
        return (
            self.step_key == self.session.current
            or self.step_key in self.session.completed
        )

    # ---------- DISPATCH ----------

    def dispatch(self, request, *args, **kwargs):
        self.setup_wizard(request, **kwargs)

        if not self.can_access_step():
            return self.redirect(self.session.current)

        return super().dispatch(request, *args, **kwargs)

    # ---------- GET ----------

    def get(self, request, *args, **kwargs):
        form = self.step.get_form(
            initial=self.session.data.get(self.step.key)
        )
        return self.render(form)

    # ---------- POST ----------

    def post(self, request, *args, **kwargs):
        form = self.step.get_form(data=request.POST)

        if not self.step.can_exit(self.session, form):
            return self.render(form)

        self.step.on_exit(self.session, form)
        self.session.complete_step(self.step.key, form.cleaned_data)

        next_key = self.workflow.next_step(self.step.key)

        if next_key:
            self.session.go_to(next_key)
            return self.redirect(next_key)

        # Wizard finished
        self.session.reset()
        return self.on_finish()

    # ---------- RENDER ----------

    def render(self, form):
        return render(
            self.request,
            self.step.template_name,
            {
                "wizard": self.workflow,
                "step": self.step,
                "steps": self.workflow.steps,
                "form": form,
                "state": self.session.state,
                "current_step": self.step.key,
                "prev_step": self.workflow.previous_step(self.step.key),
                "next_step": self.workflow.next_step(self.step.key),
            }
        )

    # ---------- REDIRECT ----------

    def redirect(self, step_key):
        url = reverse(
            "wizard:step",
            args=[self.workflow.key, step_key]
        )

        if self.request.headers.get("HX-Request"):
            return HttpResponse(
                status=204,
                headers={"HX-Redirect": url}
            )
        return redirect(url)

    # ---------- FINISH ----------

    def on_finish(self):
        """
        Override in concrete wizard views if needed
        """
        return redirect("/")
