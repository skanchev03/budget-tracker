from django.conf import settings
from django.utils import translation


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            language = request.user.language

            supported_languages = {
                code for code, _ in settings.LANGUAGES
            }

            if language in supported_languages:
                translation.activate(language)
                request.LANGUAGE_CODE = language

        response = self.get_response(request)

        translation.deactivate()

        return response