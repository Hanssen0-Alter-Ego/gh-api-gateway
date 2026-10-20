import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('gateway', Path(__file__).parents[1] / 'gh_api_gateway.py')
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.binary = Path(self.directory.name) / 'mock-gh'
        self.binary.touch()
        self.args = ['--gh', str(self.binary), '--api-host', 'gateway.example.com', '--', 'user']
        self.environment = patch.dict(os.environ, {
            'GH_TOKEN': 'synthetic-test-value', 'GITHUB_TOKEN': 'synthetic-alternative',
            'GH_ENTERPRISE_TOKEN': 'synthetic-alternative', 'GITHUB_ENTERPRISE_TOKEN': 'synthetic-alternative',
            'GH_DEBUG': 'api', 'DEBUG': '1', 'GH_CONFIG_DIR': '/unused/example', 'GH_HOST': 'example.com'
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_routing_environment_and_cleanup(self):
        calls = []
        def run(args, env):
            profile = Path(env['GH_CONFIG_DIR'])
            self.assertTrue(profile.is_dir())
            self.assertEqual(profile.stat().st_mode & 0o777, 0o700)
            self.assertEqual(env['GH_TOKEN'], 'synthetic-test-value')
            for name in ('GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'GH_DEBUG', 'DEBUG'):
                self.assertNotIn(name, env)
            calls.append((args, dict(env)))
            return subprocess.CompletedProcess(args, 0)
        with patch.object(gateway.subprocess, 'run', side_effect=run):
            self.assertEqual(gateway.main(self.args), 0)
        self.assertEqual(calls[0][0][1:], ['config', 'set', 'api_host', 'gateway.example.com', '--host', 'github.com'])
        self.assertEqual(calls[1][0][1:], ['api', '--hostname', 'github.com', 'user'])
        self.assertFalse(Path(calls[0][1]['GH_CONFIG_DIR']).exists())
        self.assertEqual(os.environ['GH_CONFIG_DIR'], '/unused/example')

    def test_missing_token_does_not_run_cli(self):
        del os.environ['GH_TOKEN']
        with patch.object(gateway.subprocess, 'run') as run:
            self.assertEqual(gateway.main(self.args), 4)
            run.assert_not_called()

    def test_configuration_failure_stops_api(self):
        with patch.object(gateway.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)) as run:
            self.assertEqual(gateway.main(self.args), 7)
            self.assertEqual(run.call_count, 1)
            self.assertFalse(Path(run.call_args.kwargs['env']['GH_CONFIG_DIR']).exists())

    def test_api_exit_status(self):
        with patch.object(gateway.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 9)]):
            self.assertEqual(gateway.main(self.args), 9)

    def test_rejects_host_override_and_absolute_url(self):
        for extra in ('--hostname=example.com', '--hostname', 'https://example.com/user'):
            with self.subTest(extra=extra), patch.object(gateway.subprocess, 'run') as run:
                with self.assertRaises(SystemExit):
                    gateway.main(self.args + [extra])
                run.assert_not_called()

    def test_rejects_invalid_gateway(self):
        for host in ('https://example.com', 'user@example.com', 'example.com/path', '-bad.example', 'example.com:443'):
            args = self.args.copy()
            args[3] = host
            with self.subTest(host=host), self.assertRaises(SystemExit):
                gateway.main(args)

    def test_exception_cleans_profile(self):
        profiles = []
        def run(args, env):
            profiles.append(env['GH_CONFIG_DIR'])
            raise OSError('synthetic failure')
        with patch.object(gateway.subprocess, 'run', side_effect=run), self.assertRaises(OSError):
            gateway.main(self.args)
        self.assertFalse(Path(profiles[0]).exists())


if __name__ == '__main__':
    unittest.main()
