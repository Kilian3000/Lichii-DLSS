from pathlib import Path
import json
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
baseline = json.loads((root/'baseline-integration.json').read_text())
launch = baseline['launch.sh']
old = '    eglantine) app_dir=/userdata/system/eglantine; config_name=eglantine; window_name=Eglantine ;;'
assert old in launch
launch = launch.replace(old, old + '\n    lichii-dlss) app_dir=/userdata/system/lichii-dlss; config_name=lichii; window_name=Lichii ;;')
old = 'python3 /userdata/system/streaming-control/switch2-session.py "$emulator" "$config_file"'
new = '''controller_family="$emulator"
normal_config="$common_dir/profile/config/lichii/qt-config.ini"
sync_shared_controls_back() {
    if [[ "$emulator" == lichii-dlss ]]; then
        python3 "$common_dir/sync-controller-config.py" "$config_file" "$normal_config"
    fi
}
if [[ "$emulator" == lichii-dlss ]]; then
    python3 "$common_dir/sync-controller-config.py" "$normal_config" "$config_file"
    controller_family=lichii
    trap sync_shared_controls_back EXIT
fi
python3 /userdata/system/streaming-control/switch2-session.py "$controller_family" "$config_file"'''
assert old in launch
launch = launch.replace(old, new)
old = '''    if "$cursor_shown"; then
        batocera-mouse hide >/dev/null 2>&1 || true
    fi
}'''
assert old in launch
launch = launch.replace(old,old[:-1]+'    sync_shared_controls_back\n}')
(root/'launch.sh').write_text(launch)

updater = baseline['update-emulators.py']
old = "repositories = {'lichii': 'zortos293/Lichii', 'eglantine': 'Eglantine-Community/Eglantine'}"
assert old in updater
updater = updater.replace(old, "repositories = {'lichii': 'zortos293/Lichii', 'eglantine': 'Eglantine-Community/Eglantine',\n                'lichii-dlss': 'Kilian3000/Lichii-DLSS'}")
old = '''    eligible = [r for r in releases if not r['draft'] and
                (r['tag_name'].startswith(('daily-', 'v0.')) if name == 'eglantine'
                 else r['name'].lower().startswith('lichii nx2 build '))]'''
new = '''    def compatible_release(release):
        if release['draft']:
            return False
        if name == 'eglantine':
            return release['tag_name'].startswith(('daily-', 'v0.'))
        if name == 'lichii-dlss':
            return release['tag_name'].startswith('dlss-build-')
        return release['name'].lower().startswith('lichii nx2 build ')
    eligible = [r for r in releases if compatible_release(r)]'''
assert old in updater
updater = updater.replace(old,new)
(root/'update-emulators.py').write_text(updater)

menu = baseline['update-emulators.sh']
menu = menu.replace('3  Update both\\n', '3  Update Lichii and Eglantine\\n')
old = "printf '4  Use the previous Lichii build\\n5  Use the previous Eglantine build\\n0  Cancel\\n\\n'"
new = "printf '4  Use the previous Lichii build\\n5  Use the previous Eglantine build\\n6  Update Lichii DLSS\\n7  Use the previous Lichii DLSS build\\n0  Cancel\\n\\n'"
assert old in menu
menu = menu.replace(old,new)
old = '    *) exit 0 ;;'
assert old in menu
menu = menu.replace(old,'''    6) python3 -u /userdata/system/lichii/update-emulators.py lichii-dlss ;;
    7) python3 -u /userdata/system/lichii/update-emulators.py lichii-dlss --rollback ;;
'''+old)
(root/'update-emulators.sh').write_text(menu)

systems = ET.fromstring(baseline['es_systems_switch2.cfg'])
emulators = systems.find('system/emulators')
entry = ET.SubElement(emulators,'emulator',name='lichii-dlss')
ET.SubElement(ET.SubElement(entry,'cores'),'core',default='true').text = 'lichii-dlss'
ET.indent(systems,space='  ')
(root/'es_systems_switch2.cfg').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(systems,encoding='unicode')+'\n')
features = ET.fromstring(baseline['es_features_switch2.cfg'])
ET.SubElement(features,'emulator',name='lichii-dlss',features='')
ET.indent(features,space='  ')
(root/'es_features_switch2.cfg').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(features,encoding='unicode')+'\n')
(root/'lichii-dlss-settings.desktop').write_text('''[Desktop Entry]
Version=1.0
Name=Lichii DLSS Settings
Comment=Configure the experimental Linux DLSS emulator
Type=Application
Exec=/userdata/system/lichii/launch.sh --emulator lichii-dlss --settings
Icon=/userdata/system/lichii/lichii.png
Terminal=false
Categories=Game;batocera.linux;
''')
print('Prepared an independent emulator entry, shared controller preferences and separate updater options')
