from django.shortcuts import HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from re import compile

EXEMPT_URLS = [compile(settings.LOGIN_URL.lstrip('/')), compile('signup')]

class AuthRequiredMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        if not request.user.is_authenticated:
            path = request.path_info.lstrip('/')
            if not any(m.match(path) for m in EXEMPT_URLS):
                return HttpResponseRedirect(reverse('login'))
        # Code to be executed for each request/response after
        # the view is called.
        return response
