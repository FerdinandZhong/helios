"""CAI entry point. Keep the Workbench kernel alive while supervising the server."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import signal

repo = Path(os.environ.get('HELIOS_ROOT') or os.environ.get('CDSW_PROJECT_DIR') or Path.cwd()).resolve()
sys.path.insert(0, str(repo))
from cai_amp.config import environment, require_cai, root


def main():
    repo = root()
    env = environment(repo)
    require_cai(env)
    python = repo / '.venv-helios-amp/bin/python'
    if not python.is_file():
        raise RuntimeError('Run the AMP setup job before starting Helios.')
    child = subprocess.Popen([str(python), '-I', str(repo / 'cai_amp/server.py')], cwd=repo, env=env, start_new_session=True)
    print(f'Helios server started as child process {child.pid}', flush=True)
    previous = signal.getsignal(signal.SIGTERM)
    def stop(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, stop)
    try:
        result = child.wait()
        if result:
            raise RuntimeError(f'Helios server exited with status {result}.')
    finally:
        try:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
        finally:
            signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    main()
