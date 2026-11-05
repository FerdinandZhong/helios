"""Explicit administrator action: create an organization and grant one native admin."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(repo), str(repo / 'shared')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', required=True, help='Exact remote-user value supplied by CAI ingress')
    parser.add_argument('--organization', required=True)
    parser.add_argument('--name', required=True, help='Name used only when creating the organization')
    args = parser.parse_args()
    if not args.username.strip() or ':' in args.username or any(c.isspace() for c in args.username):
        parser.error('Use the exact nonempty CAI remote-user value without spaces or a colon.')
    if not args.organization.strip() or not args.name.strip():
        parser.error('Organization ID and name must not be empty.')
    from cai_amp.config import environment
    os.environ.update(environment(repo))
    from helios_core.domain import Organization
    from helios_core.metadata import SQLiteMetadataRepository
    from helios_core.metadata.users import main as users
    repository = SQLiteMetadataRepository()
    repository.migrate()
    if repository.organization(args.organization) is None:
        repository.save_organization(Organization(args.organization, args.name), slug=args.organization)
    users(['add', '--username', args.username, '--role', 'org_admin', '--organization', args.organization])


if __name__ == '__main__':
    main()
