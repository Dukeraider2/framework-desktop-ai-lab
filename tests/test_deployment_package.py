from __future__ import annotations

import hashlib
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DeploymentPackageTests(unittest.TestCase):
    def test_bundle_is_buildable_checksummed_and_excludes_bytecode(self):
        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run([str(ROOT / "scripts/package-hermes-project-awareness.sh"), temp],
                                       cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            archive = Path(temp) / "hermes-project-awareness-0.2.0.tar.gz"
            checksum = Path(str(archive) + ".sha256")
            expected = checksum.read_text().split()[0]
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), expected)
            with tarfile.open(archive, "r:gz") as package:
                names = package.getnames()
                self.assertIn("hermes-project-awareness/usr/share/hermes-project-awareness/deploy/rollback.sh", names)
                self.assertIn("hermes-project-awareness/opt/hermes-project-awareness/docs/operator-runbook.md", names)
                has_dispatch_unit = (ROOT / "systemd/hermes-agent-dispatch.service").is_file()
                self.assertEqual(any(name.endswith("/systemd/hermes-agent-dispatch.service") for name in names),
                                 has_dispatch_unit)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                manifest = package.extractfile("hermes-project-awareness/SHA256SUMS")
                self.assertIsNotNone(manifest)
                for line in manifest.read().decode("utf-8").splitlines():
                    digest, relative = line.split("  ", 1)
                    relative = relative.removeprefix("./")
                    content = package.extractfile("hermes-project-awareness/" + relative)
                    self.assertIsNotNone(content, relative)
                    self.assertEqual(hashlib.sha256(content.read()).hexdigest(), digest, relative)


if __name__ == "__main__":
    unittest.main()
