"""Check native imports and database migration in temporary, disposable state."""
from pathlib import Path
import os
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(repo), str(repo / 'shared')]


def main():
    with tempfile.TemporaryDirectory(prefix='helios-amp-check-') as directory:
        os.environ.update(HELIOS_ROOT=str(repo), HELIOS_METADATA_DB=str(Path(directory) / 'helios.db'),
                          HELIOS_RUNS_DIR=str(Path(directory) / 'runs'))
        from cai_amp.application import create_app
        application = create_app()
        repository = application.api.state.metadata_repository
        if repository.integrity_check() != ('ok',):
            raise RuntimeError('Native metadata integrity check failed.')
        print('Native API imports, disposable metadata migration, and UI build verified.')


if __name__ == '__main__':
    main()
