import json
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from config import load_config, read_env
spec = importlib.util.spec_from_file_location('download_model', ROOT / 'scripts/download-model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigurationTest(unittest.TestCase):
    def test_environment_overrides_file_without_shell_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.env.example').write_text('BONSAI_CTX_SIZE=4096\nBONSAI_PORT=53110\n')
            (root / '.env').write_text('BONSAI_CTX_SIZE=2048\nLITERAL="$(touch sentinel)"\n')
            with patch.dict(os.environ, {'BONSAI_CTX_SIZE': '8192'}):
                cfg = load_config(root)
            self.assertEqual(cfg['BONSAI_CTX_SIZE'], '8192')
            self.assertEqual(cfg['BONSAI_PORT'], '53110')
            self.assertEqual(cfg['LITERAL'], '$(touch sentinel)')
            self.assertFalse((root / 'sentinel').exists())

    def test_setup_preserves_existing_options_and_secret(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            for name in ['config.py', 'setup.py']:
                (root / 'scripts' / name).write_text((ROOT / 'scripts' / name).read_text())
            (root / '.env.example').write_text('BONSAI_API_KEY=\nBONSAI_CTX_SIZE=4096\n')
            subprocess.run([sys.executable, str(root/'scripts/setup.py')], check=True, capture_output=True)
            first = read_env(root/'.env')
            self.assertTrue(first['BONSAI_API_KEY'])
            (root/'.env').write_text((root/'.env').read_text().replace('4096', '2048'))
            subprocess.run([sys.executable, str(root/'scripts/setup.py')], check=True, capture_output=True)
            second = read_env(root/'.env')
            self.assertEqual(first['BONSAI_API_KEY'], second['BONSAI_API_KEY'])
            self.assertEqual(second['BONSAI_CTX_SIZE'], '2048')
            self.assertEqual((root/'.env').stat().st_mode & 0o777, 0o600)

    def test_verified_model_is_reused_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = b'valid test model'
            (root/'test.gguf').write_bytes(content)
            cfg = {'MODEL_DIR': '.', 'MODEL_FILE': 'test.gguf', 'MODEL_SHA256': hashlib.sha256(content).hexdigest()}
            with patch('urllib.request.urlopen') as fetch:
                self.assertEqual(module.download(cfg, root), root/'test.gguf')
                fetch.assert_not_called()

    def test_corrupt_existing_model_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root/'test.gguf'
            target.write_bytes(b'existing content')
            cfg = {'MODEL_DIR': '.', 'MODEL_FILE': 'test.gguf', 'MODEL_SHA256': 'a'*64}
            with self.assertRaisesRegex(ValueError, 'checksum'):
                module.download(cfg, root)
            self.assertEqual(target.read_bytes(), b'existing content')

    def test_model_filename_cannot_escape_directory(self):
        with self.assertRaisesRegex(ValueError, 'basename'):
            module.download({'MODEL_FILE': '../escape.gguf'})


class EntrypointTests(unittest.TestCase):
    def run_entrypoint(self, settings):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = root / 'server'
            fake.write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
            fake.chmod(0o700)
            script = root / 'entrypoint'
            script.write_text((ROOT/'docker/entrypoint.sh').read_text().replace('/opt/bonsai/llama-server', str(fake)))
            env = {**os.environ, 'LLAMA_API_KEY': 'test-only', **settings}
            result = subprocess.run(['sh', str(script), 'literal $(touch sentinel)'], env=env,
                                    capture_output=True, text=True, check=True, cwd=root)
            self.assertFalse((root/'sentinel').exists())
            return json.loads(result.stdout)

    def test_native_template_keeps_kwargs_as_one_literal_argument(self):
        kwargs = '{"enable_thinking":false}'
        args = self.run_entrypoint({'BONSAI_CHAT_TEMPLATE':'auto', 'BONSAI_JINJA':'true', 'BONSAI_CHAT_TEMPLATE_KWARGS':kwargs})
        self.assertIn('--jinja', args)
        self.assertNotIn('--chat-template', args)
        self.assertEqual(args[args.index('--chat-template-kwargs')+1], kwargs)
        self.assertIn('literal $(touch sentinel)', args)

    def test_explicit_legacy_template_still_works(self):
        args = self.run_entrypoint({'BONSAI_CHAT_TEMPLATE':'chatml', 'BONSAI_JINJA':'false', 'BONSAI_CHAT_TEMPLATE_KWARGS':''})
        self.assertIn('--no-jinja', args)
        self.assertEqual(args[args.index('--chat-template')+1], 'chatml')
        self.assertNotIn('--chat-template-kwargs', args)


if __name__ == '__main__':
    unittest.main()
