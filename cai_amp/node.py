"""Install a checksum-pinned build tool without sudo or shell profile changes."""
from __future__ import annotations

import hashlib
import platform
from pathlib import Path
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen

VERSION = '22.23.3'
# https://nodejs.org/download/release/v22.23.3/SHASUMS256.txt
DIGESTS = {
    ('Linux', 'x86_64'): ('linux-x64', '1084aa36196bba4c3a5e69a1ee388a6e4ff729dad09445fbcd434b28fe3c24af'),
    ('Linux', 'aarch64'): ('linux-arm64', '5ced2d48d1d7198739b7f86804de0171aefb6823b684b12341d3321afc3cb0b2'),
    ('Darwin', 'arm64'): ('darwin-arm64', '23b25245dcfb9af7262f8ff142e9e2e0af025368117329e7a7458a51e5922f53'),
    ('Darwin', 'x86_64'): ('darwin-x64', '8a677b0219178efd6eb0e475457c4afb452b521a92f6e67845a73bd85727f2a8'),
}


def install(repo: Path) -> Path:
    spec = DIGESTS.get((platform.system(), platform.machine()))
    if spec is None:
        raise RuntimeError('Unsupported Node build platform; use a supported Linux CAI runtime.')
    platform_name, expected = spec
    name = f'node-v{VERSION}-{platform_name}'
    tools = repo / '.amp-tools'
    tools.mkdir(exist_ok=True)
    target = tools / name
    marker = target / '.verified-sha256'
    if marker.is_file() and marker.read_text().strip() == expected and (target / 'bin/node').is_file():
        return target / 'bin'
    if target.exists():
        raise RuntimeError(f'Incomplete Node installation at {target}; move it aside before retrying setup.')
    with tempfile.TemporaryDirectory(dir=tools) as work:
        work = Path(work)
        archive = work / (name + '.tar.gz')
        digest = hashlib.sha256()
        with urlopen(f'https://nodejs.org/download/release/v{VERSION}/{name}.tar.gz', timeout=60) as response, archive.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError('Node archive checksum mismatch; installation stopped.')
        with tarfile.open(archive) as package:
            package.extractall(work, filter='data')
        extracted = work / name
        version = subprocess.check_output([str(extracted / 'bin/node'), '--version'], text=True).strip()
        if version != f'v{VERSION}':
            raise RuntimeError('Unexpected Node version.')
        (extracted / '.verified-sha256').write_text(expected + '\n')
        extracted.rename(target)
    return target / 'bin'
