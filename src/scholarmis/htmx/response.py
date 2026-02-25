import json
from django.template.loader import render_to_string
from django.http import HttpResponse
from scholarmis.framework.urls import safe_reverse


class HTMXResponse:
    
    @staticmethod
    def render(request, template=None, context=None, extra_partials=None, **kwargs ):
        context = context or {}
        html_parts = []

        if template:
            html_parts.append(render_to_string(template, context, request=request))

        if extra_partials:
            for pt in extra_partials:
                html_parts.append(render_to_string(pt, context, request=request))

        response = HttpResponse("".join(html_parts))
        return HTMXResponse._add_headers(response, **kwargs)

    @staticmethod
    def redirect(url, target=None, swap=None, refresh=False, **kwargs):
        """
        Handles navigation. 
        - refresh=True: Full browser reload (HX-Redirect).
        - refresh=False: AJAX navigation (HX-Location).
        """
        response = HttpResponse()
        if refresh:
            response["HX-Redirect"] = url
        else:
            location = {"path": url}
            if target: location["target"] = target
            if swap: location["swap"] = swap
            response["HX-Location"] = json.dumps(location)
            
        return HTMXResponse._add_headers(response, **kwargs)

    @staticmethod
    def _add_headers(
        response, 
        retarget=None, 
        reswap=None, 
        trigger=None, 
        push_url=None, 
        replace_url=None,
        trigger_after_settle=None,
        trigger_after_swap=None
    ):
        """Attaches all supported HTMX control headers."""
        
        # Target & Swap overrides
        if retarget: response["HX-Retarget"] = retarget
        if reswap: response["HX-Reswap"] = reswap
        
        # History Management
        if push_url:
            response["HX-Push-Url"] = "true" if push_url is True else push_url
        if replace_url:
            response["HX-Replace-Url"] = "true" if replace_url is True else replace_url

        # Event Triggers (Immediate, After Settle, After Swap)
        if trigger:
            response["HX-Trigger"] = json.dumps(trigger) if isinstance(trigger, dict) else trigger
        if trigger_after_settle:
            response["HX-Trigger-After-Settle"] = json.dumps(trigger_after_settle) if isinstance(trigger_after_settle, dict) else trigger_after_settle
        if trigger_after_swap:
            response["HX-Trigger-After-Swap"] = json.dumps(trigger_after_swap) if isinstance(trigger_after_swap, dict) else trigger_after_swap
            
        return response


def htmx_render(request, template, context=None, **kwargs):
    """
    Renders a partial with stateless Message objects.
    'alerts' can be a string, a Message object, or a list of either.
    """

    return HTMXResponse.render(
        request, 
        template, 
        context, 
        **kwargs
    )


def htmx_redirect(url, **kwargs):
    """
    Shortcut for HTMX-native redirects (HX-Location).
    Usage: return htmx_redirect('/dashboard/')
    """
    return HTMXResponse.redirect(url, refresh=False, **kwargs)


def htmx_refresh(url, **kwargs):
    """
    Shortcut for full-page refreshes (HX-Redirect).
    Usage: return htmx_refresh('/login/')
    """
    return HTMXResponse.redirect(url, refresh=True, **kwargs)


def htmx_partial(request, extra_partials, **kwargs):
    """
    Shortcut for updating OOB fragments WITHOUT changing the main target.
    Usage: return htmx_partial(request, ['sidebar.html'])
    """
    return HTMXResponse.render(request, template=None, extra_partials=extra_partials, **kwargs)


def htmx_safe_redirect(view_name, app_name=None, args=None, **kwargs):
    url = safe_reverse(view_name, app_name, args)
    return htmx_redirect(url, **kwargs)


def htmx_safe_refresh(view_name, app_name=None, args=None, **kwargs):
    url = safe_reverse(view_name, app_name, args)
    return htmx_refresh(url, **kwargs)
