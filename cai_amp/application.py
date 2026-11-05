"""One authenticated origin for the unmodified native API and React UI."""
from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles


class UIStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        if '..' in scope.get('path', '').split('/'):
            raise HTTPException(404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith('assets/') or Path(path).suffix:
                raise
            response = await super().get_response('index.html', scope)
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if path.startswith('assets/') else 'no-cache'
        return response


class CombinedApplication:
    def __init__(self, api, dist: Path):
        if not (dist / 'index.html').is_file():
            raise RuntimeError('Run cai_amp/setup.py before starting the Application.')
        self.api = api

        async def config(request):
            return Response('window.__HELIOS_CONFIG__ = {apiUrl: window.location.origin};\n',
                            media_type='text/javascript', headers={'Cache-Control': 'no-store'})

        async def health(request):
            return PlainTextResponse('ok\n')

        self.ui = Starlette(routes=[Route('/config.js', config), Route('/healthz', health),
                                    Mount('/', UIStaticFiles(directory=dist, html=True))])

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        aliases = {'/api/docs': '/docs', '/api/docs/oauth2-redirect': '/docs/oauth2-redirect',
                   '/api/redoc': '/redoc', '/api/openapi.json': '/openapi.json'}
        api_path = path == '/api' or path.startswith('/api/') or path == '/openapi.json'
        if path in aliases:
            scope = dict(scope, path=aliases[path], raw_path=aliases[path].encode())
        # Preserve incoming identity headers, streaming responses, and API lifespan.
        application = self.api if scope['type'] != 'http' or api_path else self.ui
        await application(scope, receive, send)


def create_app():
    from cai_amp.config import root
    from apps.helios.console.main import app
    return CombinedApplication(app, root() / 'apps/helios/ui/dist')
