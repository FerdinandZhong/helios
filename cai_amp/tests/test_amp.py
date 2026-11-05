from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from cai_amp.application import CombinedApplication
from cai_amp.config import environment, require_cai


@pytest.fixture
def client(tmp_path):
    (tmp_path / 'index.html').write_text('<html>native Helios</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/app-hash.js').write_text('console.log("native")')
    state = []
    @asynccontextmanager
    async def lifespan(app):
        state.append('started')
        yield
        state.append('stopped')
    api = FastAPI(lifespan=lifespan)
    @api.get('/api/v1/identity')
    def identity(request: Request):
        subject = request.headers.get('remote-user')
        if not subject:
            raise HTTPException(401)
        return {'subject': subject, 'path': request.url.path}
    @api.get('/api/v1/events')
    def events():
        return StreamingResponse(iter(['data: first\n\n', 'data: last\n\n']), media_type='text/event-stream')
    with TestClient(CombinedApplication(api, tmp_path)) as active:
        assert state == ['started']
        yield active
    assert state == ['started', 'stopped']


def test_native_identity_and_api_paths_are_preserved(client):
    assert client.get('/api/v1/identity').status_code == 401
    result = client.get('/api/v1/identity', headers={'remote-user': 'alice'})
    assert result.json() == {'subject': 'alice', 'path': '/api/v1/identity'}
    missing = client.get('/api/v1/missing')
    assert missing.status_code == 404 and missing.headers['content-type'] == 'application/json'


def test_streams_and_openapi_reach_native_api(client):
    assert client.get('/api/v1/events').text == 'data: first\n\ndata: last\n\n'
    assert '/api/v1/identity' in client.get('/openapi.json').json()['paths']
    assert 'swagger-ui' in client.get('/api/docs').text
    assert '/api/v1/identity' in client.get('/api/openapi.json').json()['paths']


def test_browser_config_uses_same_origin_without_a_key(client):
    result = client.get('/config.js', headers={'host': 'untrusted.example'})
    assert result.text == 'window.__HELIOS_CONFIG__ = {apiUrl: window.location.origin};\n'
    assert result.headers['cache-control'] == 'no-store'


def test_native_spa_and_asset_cache_policy(client):
    for path in ['/', '/models', '/organizations/demo/models/finance', '/docs', '/docs/helios/walkthrough']:
        response = client.get(path)
        assert response.status_code == 200 and 'native Helios' in response.text
        assert response.headers['cache-control'] == 'no-cache'
    assert 'immutable' in client.get('/assets/app-hash.js').headers['cache-control']
    assert client.get('/assets/old-build.js').status_code == 404
    assert client.get('/missing.js').status_code == 404
    assert client.get('/%2e%2e/%2e%2e/etc/passwd').status_code == 404


def test_missing_build_fails_startup(tmp_path):
    with pytest.raises(RuntimeError, match='setup'):
        CombinedApplication(FastAPI(), tmp_path)


def test_environment_keeps_state_and_credentials_but_excludes_notebook_packages(monkeypatch, tmp_path):
    monkeypatch.setenv('PYTHONPATH', '/vendor/notebook')
    monkeypatch.setenv('PIP_TARGET', '/vendor/packages')
    monkeypatch.setenv('HELIOS_METADATA_DB', '/persistent/native.db')
    monkeypatch.setenv('CDSW_APIV2_KEY', 'test-secret')
    env = environment(tmp_path)
    assert 'PYTHONPATH' not in env and 'PIP_TARGET' not in env
    assert env['HELIOS_METADATA_DB'] == '/persistent/native.db'
    assert env['CDSW_APIV2_KEY'] == 'test-secret'
    assert env['HELIOS_ROOT'] == str(tmp_path)


@pytest.mark.parametrize('bad', [{'HELIOS_DEV':'1'}, {'HELIOS_DEV_USER':'alice'}, {'CDSW_APP_PORT':'0'}, {'CDSW_PROJECT_ID':''}])
def test_cai_requires_ingress_and_rejects_development_identity(bad):
    env = {'CDSW_APP_PORT':'8080', 'CDSW_PROJECT_ID':'project', 'CDSW_DOMAIN':'example.com'} | bad
    with pytest.raises((ValueError, RuntimeError)):
        require_cai(env)


def test_manifest_installs_before_starting_authenticated_application():
    repo = Path(__file__).resolve().parents[2]
    manifest = yaml.safe_load((repo / '.project-metadata.yaml').read_text())
    assert [task['type'] for task in manifest['tasks']] == ['create_job', 'run_job', 'start_application']
    assert manifest['tasks'][1]['wait_for'] is True
    assert manifest['tasks'][-1]['bypass_authentication'] is False
    for task in manifest['tasks']:
        if 'script' in task:
            assert (repo / task['script']).is_file()


def test_launcher_propagates_child_failure_and_restores_handler(monkeypatch, tmp_path):
    from cai_amp import launch
    from unittest.mock import Mock
    executable = tmp_path / '.venv-helios-amp/bin/python'
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(launch, 'root', lambda: tmp_path)
    monkeypatch.setattr(launch, 'require_cai', lambda env: 8080)
    child = Mock(pid=123)
    child.wait.return_value = 7
    child.poll.return_value = 7
    spawn = Mock(return_value=child)
    monkeypatch.setattr(launch.subprocess, 'Popen', spawn)
    original = launch.signal.getsignal(launch.signal.SIGTERM)
    with pytest.raises(RuntimeError, match='status 7'):
        launch.main()
    assert launch.signal.getsignal(launch.signal.SIGTERM) == original
    assert spawn.call_args.kwargs['start_new_session'] is True


def test_node_checksum_failure_does_not_install(monkeypatch, tmp_path):
    import io
    from cai_amp import node
    monkeypatch.setattr(node.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(node.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(node, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'corrupted archive'))
    with pytest.raises(RuntimeError, match='checksum'):
        node.install(tmp_path)
    assert not (tmp_path / '.amp-tools' / f'node-v{node.VERSION}-linux-x64').exists()
