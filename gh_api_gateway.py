#!/usr/bin/env python3
"""Run gh api through an explicitly selected, already authorized gateway."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gh', required=True, help='absolute path to the real gh executable')
    parser.add_argument('--api-host', required=True, help='authorized HTTPS gateway hostname')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='-- followed by gh api arguments')
    options = parser.parse_args(argv)
    executable = Path(options.gh)
    if not executable.is_absolute() or not executable.is_file():
        parser.error('--gh must name an existing absolute executable path')
    host = options.api_host
    if len(host) > 253 or not all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
                                 for label in host.split('.')):
        parser.error('--api-host must be a hostname without scheme, port, path or credentials')
    args = options.args
    if args[:1] == ['--']:
        args = args[1:]
    if not args:
        parser.error('provide gh api arguments after --')
    if any(arg == '--hostname' or arg.startswith('--hostname=') or '://' in arg for arg in args):
        parser.error('use relative API endpoints and the fixed logical host github.com')
    env = os.environ.copy()
    if not env.get('GH_TOKEN'):
        print('GH_TOKEN is required; no alternate credential is selected.', file=sys.stderr)
        return 4
    for name in ('GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'GH_DEBUG', 'DEBUG'):
        env.pop(name, None)
    # A fresh profile prevents loading persisted gh credentials, aliases or host settings.
    with tempfile.TemporaryDirectory(prefix='gh-api-gateway-') as profile:
        env.update(GH_CONFIG_DIR=profile, GH_HOST='github.com', GH_PROMPT_DISABLED='1',
                   GH_NO_UPDATE_NOTIFIER='1')
        configured = subprocess.run([str(executable), 'config', 'set', 'api_host', host,
                                     '--host', 'github.com'], env=env)
        if configured.returncode:
            return configured.returncode
        return subprocess.run([str(executable), 'api', '--hostname', 'github.com', *args],
                              env=env).returncode


if __name__ == '__main__':
    sys.exit(main())
