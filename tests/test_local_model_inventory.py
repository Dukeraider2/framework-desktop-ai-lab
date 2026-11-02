from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts/agents/collect-local-model-inventory.py"
SPEC = importlib.util.spec_from_file_location("collect_local_model_inventory", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class LocalModelInventoryTests(unittest.TestCase):
    def test_ollama_list_parser_keeps_only_bounded_rows(self):
        with mock.patch.object(collector, "run_cli", return_value=(0,
                "NAME  ID  SIZE  MODIFIED\nqwen3:30b  abcdef0123456789  18 GB  2 days ago\n"
                "bad name with spaces  id  1 GB  now\n", "")):
            self.assertEqual(collector.installed_models(), [{
                "name": "qwen3:30b", "id_prefix": "abcdef0123456789",
                "size": "18 GB", "modified": "2 days ago"}])

    def test_model_metadata_is_filtered_to_approved_labels(self):
        with mock.patch.object(collector, "run_cli", return_value=(0,
                "architecture: qwen3\nparameters: 30.5B\ncontext length: 32768\n"
                "license: proprietary\napi key: secret\n", "")):
            result = collector.metadata("qwen3:30b")
        self.assertEqual(result["architecture"], "qwen3")
        self.assertEqual(result["parameters"], "30.5B")
        self.assertNotIn("license", result)
        self.assertNotIn("api_key", result)

    def test_benchmark_rejects_invalid_names_before_network(self):
        with mock.patch.object(collector.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(ValueError):
                collector.benchmark("../../etc/passwd")
            urlopen.assert_not_called()

    def test_benchmark_emits_only_counters_and_timing(self):
        payload = {"total_duration": 5_000_000_000, "load_duration": 1_000_000_000,
                   "prompt_eval_count": 12, "prompt_eval_duration": 1_000_000_000,
                   "eval_count": 32, "eval_duration": 2_000_000_000,
                   "response": "secret generated text"}

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, _limit):
                import json
                return json.dumps(payload).encode()

        with mock.patch.object(collector.urllib.request, "urlopen", return_value=Response()) as urlopen:
            result = collector.benchmark("local-model:latest")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertIn("/api/generate", request.full_url)
        self.assertNotIn("response", result)
        self.assertEqual(result["eval_tokens_per_second"], 16.0)
        self.assertEqual(result["prompt_tokens_per_second"], 12.0)


if __name__ == "__main__":
    unittest.main()
