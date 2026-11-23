"""Offline tests; they do not require model weights, root, Podman, or target server."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))
import build_llama
import benchmark
import gguf_inventory
import tune


class FrameworkTests(unittest.TestCase):
    def test_tune_validate(self):
        tune.validate_changes({})
        tune.validate_changes({'/proc/sys/kernel/numa_balancing': '0'})
        with self.assertRaises(ValueError):
            tune.validate_changes({'/etc/ssh/sshd_config': 'disabled'})
        with self.assertRaises(ValueError):
            tune.validate_changes({'/proc/sys/kernel/numa_balancing': '77'})

    def test_selected_value(self):
        self.assertEqual(tune.parse_selected('always [madvise] never'), 'madvise')
        self.assertEqual(tune.parse_selected('0\n'), '0')

    def test_profiles(self):
        self.assertEqual(tune.read_profile('baseline'), {})
        self.assertEqual(tune.read_profile('numa-balancing-off'), {'/proc/sys/kernel/numa_balancing':'0'})
        with self.assertRaises(ValueError):
            tune.read_profile('../evil')

    def test_build_profiles(self):
        base = build_llama.make_commands(Path('/tmp/upstream'), Path('/tmp/out'), 'baseline', False)
        zen = build_llama.make_commands(Path('/tmp/upstream'), Path('/tmp/out'), 'zen1', True)
        self.assertIn('-DGGML_CPU_REPACK=OFF', base[0])
        self.assertIn('-DGGML_CPU_REPACK=ON', zen[0])
        self.assertTrue(any('-march=znver1' in s for s in zen[0]))
        self.assertFalse(any('-march=znver1' in s for s in base[0]))
        self.assertIn('-DGGML_CUDA=OFF', zen[0])
        self.assertIn('-DGGML_HIP=OFF', zen[0])
        self.assertIn('-DGGML_AVX_VNNI=OFF', zen[0])

    def test_benchmark_command(self):
        cmd = benchmark.bench_command(Path('/tmp/llama-bench'), Path('/models/test.gguf'), 64, 512, 128, 5, 'distribute')
        self.assertIn('0', cmd)
        self.assertEqual(cmd[cmd.index('-ngl') + 1], '0')
        self.assertEqual(cmd[cmd.index('--numa') + 1], 'distribute')
        with self.assertRaises(ValueError):
            benchmark.bench_command(Path('/tmp/b'), Path('/tmp/m'), 0, 512, 128, 5, 'distribute')

    def test_gguf_metadata_only(self):
        # Synthetic GGUF v3: one tensor, zero metadata, one 1D tensor with Q4_K type.
        name = b'blk.0.ffn_exps.weight'
        data = b'GGUF' + struct.pack('<IQQ', 3, 1, 0)
        data += struct.pack('<Q', len(name)) + name + struct.pack('<I', 1)
        data += struct.pack('<QIQ', 256, 12, 0)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'sample.gguf'
            path.write_bytes(data)
            obj = gguf_inventory.Parser(path)
            try:
                result = obj.parse()
            finally:
                obj.close()
            self.assertEqual(result['tensor_types'], {'Q4_K':1})
            self.assertEqual(result['potential_expert_tensor_types'], {'Q4_K':1})

    def test_gguf_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.gguf'
            path.write_bytes(b'GGUF' + struct.pack('<IQQ', 3, 1, 0))
            obj = gguf_inventory.Parser(path)
            try:
                with self.assertRaises(gguf_inventory.GGUFError):
                    obj.parse()
            finally:
                obj.close()

if __name__ == '__main__':
    unittest.main()
