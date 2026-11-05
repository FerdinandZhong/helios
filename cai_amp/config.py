"""Repository discovery, persistent paths, and isolated process environment."""
from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    candidates = [Path(os.environ.get('HELIOS_ROOT') or os.environ.get('CDSW_PROJECT_DIR') or Path.cwd()),
                  Path(__file__).resolve().parents[1]]
    for candidate in candidates:
        if (candidate / 'shared/helios_core').is_dir() and (candidate / 'cai_amp').is_dir():
            return candidate.resolve()
    raise RuntimeError('Run from the Helios checkout or set HELIOS_ROOT.')


def environment(repo: Path) -> dict[str, str]:
    env = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONUSERBASE', 'PIP_TARGET', 'PIP_PREFIX'):
        env.pop(name, None)
    target = repo / '.venv-helios-amp'
    env.update(HELIOS_ROOT=str(repo), PYTHONNOUSERSITE='1', PIP_USER='0',
               PIP_CONFIG_FILE=os.devnull, VIRTUAL_ENV=str(target))
    env['PATH'] = str(target / 'bin') + os.pathsep + env.get('PATH', '')
    env.setdefault('HELIOS_METADATA_DB', str(repo / 'state/helios.db'))
    env.setdefault('HELIOS_SQLITE_JOURNAL_MODE', 'DELETE')
    return env


def require_cai(env: dict[str, str]) -> int:
    if not all(env.get(k) for k in ('CDSW_APP_PORT', 'CDSW_PROJECT_ID', 'CDSW_DOMAIN')):
        raise RuntimeError('CAI Application context is required. Use the documented local server command for local checks.')
    if env.get('HELIOS_DEV') not in (None, '', '0') or env.get('HELIOS_DEV_USER'):
        raise RuntimeError('Remove HELIOS_DEV and HELIOS_DEV_USER before CAI launch.')
    port = int(env['CDSW_APP_PORT'])
    if not 1 <= port <= 65535:
        raise RuntimeError('CDSW_APP_PORT is invalid.')
    return port
