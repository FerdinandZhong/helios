"""AMP setup job: isolated Python dependencies and a locked native UI build."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

# Workbench notebook execution does not always define __file__.
repo = Path(os.environ.get('HELIOS_ROOT') or os.environ.get('CDSW_PROJECT_DIR') or Path.cwd()).resolve()
sys.path.insert(0, str(repo))
from cai_amp.config import environment, root
from cai_amp.node import install


def main() -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Select Standard Python 3.12 for both setup and Application.')
    repo = root()
    env = environment(repo)
    target = repo / '.venv-helios-amp'
    subprocess.run([sys.executable, '-I', '-m', 'venv', str(target)], env=env, check=True)
    python = str(target / 'bin/python')
    subprocess.run([python, '-I', '-m', 'pip', 'install', '-r', str(repo / 'cai_amp/requirements.txt')], cwd=repo, env=env, check=True)
    subprocess.run([python, '-I', '-m', 'pip', 'check'], cwd=repo, env=env, check=True)
    probe = "import pathlib,site,sys; p=pathlib.Path(sys.prefix).resolve(); assert sys.prefix!=sys.base_prefix and not site.ENABLE_USER_SITE; import importlib.metadata as m; assert all(pathlib.Path(d.locate_file('')).resolve().is_relative_to(p) for d in m.distributions())"
    subprocess.run([python, '-I', '-c', probe], env=env, check=True)
    node = install(repo)
    env['PATH'] = str(node) + os.pathsep + env['PATH']
    env.setdefault('npm_config_cache', str(repo / '.amp-tools/npm-cache'))
    ui = repo / 'apps/helios/ui'
    subprocess.run([str(node / 'npm'), 'ci'], cwd=ui, env=env, check=True)
    subprocess.run([str(node / 'npm'), 'run', 'build'], cwd=ui, env=env, check=True)
    if not (ui / 'dist/index.html').is_file():
        raise RuntimeError('Native UI build is missing.')
    subprocess.run([python, '-I', str(repo / 'cai_amp/verify.py')], cwd=repo, env=env, check=True)
    print('Helios AMP setup complete. Configure native user grants, data sources, MCP, and inference after launch.', flush=True)


if __name__ == '__main__':
    main()
