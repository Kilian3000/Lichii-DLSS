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

    def test_frame_generation_precedence_and_off(self):
        layers = {
            'global': {r.FRAME_GENERATION_KEY: '2'},
            'switch2': {r.FRAME_GENERATION_KEY: '3'},
            'switch2.folder["/roms/sub"]': {r.FRAME_GENERATION_KEY: '4'},
            'switch2["game.nup"]': {r.FRAME_GENERATION_KEY: 'auto'},
        }
        for emulator in ('lichii', 'lichii-dlss'):
            self.assertEqual(r.resolve(lambda key: layers.get(key, {}),
                                       '/roms/sub/game.nup', emulator),
                             {'frame_gen': 'true', 'frame_gen_type': '1',
                              'frame_gen_multiplier': '4', 'frame_gen_target_rate': '0'})
        layers['switch2["game.nup"]'][r.FRAME_GENERATION_KEY] = 'off'
        self.assertEqual(r.resolve(lambda key: layers.get(key, {}), '/roms/sub/game.nup', 'lichii'),
                         {'frame_gen': 'false'})
        for multiplier in ('2', '3', '4'):
            self.assertEqual(r.resolve(lambda _: {r.FRAME_GENERATION_KEY: multiplier},
                                       '/roms/game.nup')['frame_gen_multiplier'], multiplier)
        with self.assertRaises(ValueError):
            r.resolve(lambda _: {r.FRAME_GENERATION_KEY: '5'}, '/roms/game.nup', 'lichii')

    def test_original_ignores_fork_options_including_invalid_values(self):
        values = {r.STYLE_KEY: 'invalid', r.STRENGTH_KEY: 'bad', r.QUALITY_KEY: 'bogus',
                  r.FRAME_GENERATION_KEY: '2'}
        self.assertEqual(r.resolve(lambda _: values, '/roms/game.nup', 'lichii'),
                         {'frame_gen': 'true', 'frame_gen_type': '1',
                          'frame_gen_multiplier': '2', 'frame_gen_target_rate': '0'})
        values.pop(r.FRAME_GENERATION_KEY)
        self.assertEqual(r.resolve(lambda _: values, '/roms/game.nup', 'lichii'), {})
        values.update({r.STYLE_KEY: 'off', r.STRENGTH_KEY: '50', r.QUALITY_KEY: 'native',
                       r.FRAME_GENERATION_KEY: '2'})
        fork = r.resolve(lambda _: values, '/roms/game.nup')
        self.assertEqual(fork['frame_gen_multiplier'], '2')
        self.assertEqual(fork['neural_rendering'], '0')
        self.assertEqual(fork['neural_rendering_strength'], '50')
        self.assertEqual(fork['nvidia_dlss_quality'], '1')

    def test_fg_exit_and_interrupted_recovery_preserve_other_preferences(self):
        fg = {'frame_gen', 'frame_gen_type', 'frame_gen_multiplier', 'frame_gen_target_rate'}
        global_keys = fg | {key+'\\default' for key in fg}
        game_keys = fg | {key+'\\use_global' for key in fg} | {key+'\\default' for key in fg}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'custom').mkdir()
            glob = root/'qt-config.ini'
            glob.write_text('[Controls]\npad=portal\n[Renderer]\nframe_gen=false\n'
                            'frame_gen\\default=true\nframe_gen_type=2\n'
                            'frame_gen_type\\default=false\nframe_gen_multiplier=3\n'
                            'frame_gen_target_rate=90\nresolution=1\nneural_rendering=3\n')
            game = root/'custom/0123.ini'
            game.write_text('[Renderer]\nframe_gen=true\nframe_gen\\use_global=false\n'
                            'frame_gen_type=0\nframe_gen_type\\use_global=false\n'
                            'frame_gen_type\\default=true\nframe_gen_multiplier=4\n'
                            'frame_gen_multiplier\\use_global=true\nframe_gen_target_rate=144\n'
                            'resolution=2\n[Controls]\npad=gamepad\n[Core]\nlimit=100\n')
            original_global = r.read_keys(glob, global_keys)
            original_game = r.read_keys(game, game_keys)
            updates = r.resolve(lambda _: {r.FRAME_GENERATION_KEY: '2'}, '/roms/game.nup', 'lichii')
            r.apply(root, updates)
            self.assertEqual(r.read_keys(glob, fg), updates)
            self.assertEqual(r.read_keys(game, {key+'\\use_global' for key in fg}),
                             {key+'\\use_global': 'true' for key in fg})
            self.assertIn('frame_gen_type=0\n', game.read_text())
            glob.write_text(glob.read_text().replace('pad=portal', 'pad=dualsense'))
            game.write_text(game.read_text().replace('resolution=2', 'resolution=3'))
            r.restore(root)  # Same operation as normal game exit / F1 recovery.
            self.assertEqual(r.read_keys(glob, global_keys), original_global)
            self.assertEqual(r.read_keys(game, game_keys), original_game)
            self.assertIn('pad=dualsense', glob.read_text())
            self.assertIn('neural_rendering=3', glob.read_text())
            self.assertIn('resolution=3\n[Controls]\npad=gamepad\n[Core]\nlimit=100', game.read_text())
            self.assertFalse((root/r.STATE).exists())
            r.apply(root, updates)  # Simulate power loss, then launch an inherited/Auto game.
            r.apply(root, {})
            self.assertEqual(r.read_keys(glob, global_keys), original_global)
            self.assertEqual(r.read_keys(game, game_keys), original_game)
            self.assertFalse((root/r.STATE).exists())

    def test_auto_without_inherited_choice_does_not_write_other_games(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'custom').mkdir()
            paths = [root/'qt-config.ini', root/'custom/0123.ini', root/'custom/4567.ini']
            for path in paths:
                path.write_text('[Renderer]\nframe_gen_type=2\nresolution=3\n[Controls]\npad=keep\n')
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
            for emulator in ('lichii', 'lichii-dlss'):
                updates = r.resolve(lambda _: {r.FRAME_GENERATION_KEY: 'auto'}, '/roms/other.nup', emulator)
                self.assertEqual(updates, {})
                r.apply(root, updates)
            self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}, before)
            self.assertFalse((root/r.STATE).exists())

    def test_frontend_exposes_same_fg_choices_for_both_lichii_variants(self):
        import xml.etree.ElementTree as ET
        features = ET.parse(Path(__file__).with_name('es_features_switch2.cfg')).getroot()
        for emulator in ('lichii', 'lichii-dlss'):
            fg = features.find(f"./emulator[@name='{emulator}']/feature[@value='{r.FRAME_GENERATION_KEY}']")
            self.assertIsNotNone(fg)
            self.assertEqual({node.attrib['value'] for node in fg.findall('choice')}, r.FRAME_GENERATION)
        self.assertIsNone(features.find("./emulator[@name='lichii']/feature[@value='lichii_dlss_neural']"))

    def test_frontend_enum_values_match_emulator(self):
        source = Path(__file__).resolve().parents[1]/'src/common/settings_enums.h'
        if not source.exists():
            source = Path(__file__).resolve().parents[1]/'source/src/common/settings_enums.h'
        text = source.read_text()
        self.assertRegex(text, r'ENUM\(FrameGenType,\s*Lsfg,\s*OpticalFlow,\s*NvidiaDlssG\);')
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
