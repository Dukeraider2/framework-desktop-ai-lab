import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'preflight', Path(__file__).resolve().parents[1] / 'image/preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def test_windows_is_blocked_even_with_tools(self):
        result = preflight.inspect('Windows', lambda _: '/tool')
        self.assertEqual(result['status'], 'blocked')

    def test_missing_linux_tools_block(self):
        result = preflight.inspect('Linux', lambda _: None)
        self.assertEqual(len(result['blockers']), len(result['executables']))

    def test_tools_do_not_imply_build_validation(self):
        result = preflight.inspect('Linux', lambda _: '/tool')
        self.assertEqual(result['status'], 'capabilities-present')
        self.assertIn('image build and UEFI boot', result['not_validated'])
