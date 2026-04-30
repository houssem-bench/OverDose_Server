from __future__ import annotations

from urllib.parse import urlparse

from django.http import HttpResponse


class LocalCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        if request.method == "OPTIONS":
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        if self._is_allowed_origin(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

        return response

    @staticmethod
    def _is_allowed_origin(origin: str | None) -> bool:
        if not origin:
            return False

        parsed = urlparse(origin)
        if parsed.scheme != "http":
            return False

        hostname = (parsed.hostname or "").lower()
        return hostname in {"localhost", "127.0.0.1"}