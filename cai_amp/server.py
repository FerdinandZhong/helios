"""Isolated child process; also supports an explicit loopback-only local check."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(repo), str(repo / 'shared')]


def main():
    from cai_amp.config import environment, require_cai
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    env = environment(repo)
    if args.local:
        if not args.port or not 1 <= args.port <= 65535:
            parser.error('Local mode requires --port between 1 and 65535.')
        port = args.port
    else:
        port = require_cai(env)
    os.environ.update(env)
    from cai_amp.application import create_app
    import uvicorn
    uvicorn.run(create_app(), host='127.0.0.1', port=port, proxy_headers=False)


if __name__ == '__main__':
    main()
