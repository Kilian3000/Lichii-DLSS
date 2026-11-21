from pathlib import Path
import importlib.util
import tempfile
import unittest
import re

spec = importlib.util.spec_from_file_location('renderer', Path(__file__).with_name('batocera-renderer.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class SessionSettings(unittest.TestCase):
    def test_frontend_precedence_and_auto_inheritance(self):
        layers = {
            'global': {r.STYLE_KEY: 'standard'},
            'switch2': {r.STYLE_KEY: 'natural', r.STRENGTH_KEY: '75'},
            'switch2.folder["/roms/sub"]': {r.STYLE_KEY: 'cinematic'},
            'switch2["game.nup"]': {r.STYLE_KEY: 'off', r.STRENGTH_KEY: 'auto'},
        }
        self.assertEqual(r.resolve(lambda key: layers.get(key, {}), '/roms/sub/game.nup'),
                         {'neural_rendering': '0', 'neural_rendering_strength': '75'})
        self.assertEqual(r.resolve(lambda _: {}, '/roms/game.nup'), {})
        self.assertEqual(r.resolve(lambda _: {r.QUALITY_KEY: 'native'}, '/roms/game.nup'),
                         {'nvidia_dlss_quality': '1'})
        with self.assertRaises(ValueError):
            r.resolve(lambda _: {r.STYLE_KEY: 'invalid'}, '/roms/game.nup')

    def test_exit_restores_preferences_but_keeps_new_emulator_and_controller_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'custom').mkdir()
            glob = root/'qt-config.ini'
            glob.write_text('[Controls]\npad=portal\n[Renderer]\nneural_rendering=0\nneural_rendering\\default=true\nresolution=1\n')
            game = root/'custom/0123.ini'
            game.write_text('[Renderer]\nneural_rendering=3\nneural_rendering\\use_global=false\nresolution=2\n[UI]\nx=4\n')
            r.apply(root, {'neural_rendering': '2', 'nvidia_dlss': 'true'})
            self.assertEqual(r.read_keys(glob, {'neural_rendering'})['neural_rendering'], '2')
            self.assertEqual(r.read_keys(game, {'neural_rendering\\use_global'})['neural_rendering\\use_global'], 'true')
            glob.write_text(glob.read_text().replace('pad=portal', 'pad=dualsense')+'new_emulator_key=42\n')
            r.restore(root)
            self.assertIn('pad=dualsense', glob.read_text())
            self.assertIn('new_emulator_key=42', glob.read_text())
            self.assertEqual(r.read_keys(glob, {'neural_rendering', 'nvidia_dlss'}),
                             {'neural_rendering': '0', 'nvidia_dlss': None})
            self.assertIn('neural_rendering\\use_global=false', game.read_text())
            self.assertIn('resolution=2', game.read_text())
            self.assertFalse((root/r.STATE).exists())

    def test_frontend_enum_values_match_emulator(self):
        source = Path(__file__).resolve().parents[1]/'src/common/settings_enums.h'
        if not source.exists():
            source = Path(__file__).resolve().parents[1]/'source/src/common/settings_enums.h'
        text = source.read_text()
        for enum, mapping, expected in [('NeuralRendering', r.STYLES,
                                        ['Off', 'Standard', 'Natural', 'Cinematic']),
                                       ('NvidiaDlssQuality', r.QUALITIES,
                                        ['Automatic', 'Native', 'Quality', 'Balanced',
                                         'Performance', 'UltraPerformance'])]:
            found = re.search(r'ENUM\('+enum+r',\s*([^;]+)\);', text)
            self.assertIsNotNone(found)
            self.assertEqual([x.strip() for x in found.group(1).split(',')], expected)
            self.assertEqual(list(mapping.values()), [str(i) for i in range(len(expected))])

    def test_interrupted_session_recovers_before_next_game(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            glob = root/'qt-config.ini'
            glob.write_text('[Renderer]\nneural_rendering=0\n')
            r.apply(root, {'neural_rendering': '3'})
            r.apply(root, {})
            self.assertEqual(r.read_keys(glob, {'neural_rendering'})['neural_rendering'], '0')
            self.assertFalse((root/r.STATE).exists())


if __name__ == '__main__':
    unittest.main()
