#!/bin/bash
set -u
printf 'Switch 2 emulator updates\n\n'
printf '1  Update Lichii\n2  Update Eglantine\n3  Update Lichii and Eglantine\n'
printf '4  Use the previous Lichii build\n5  Use the previous Eglantine build\n6  Update Lichii DLSS\n7  Use the previous Lichii DLSS build\n0  Cancel\n\n'
read -r -p 'Choose a number: ' selection
case "$selection" in
    1) python3 -u /userdata/system/lichii/update-emulators.py lichii ;;
    2) python3 -u /userdata/system/lichii/update-emulators.py eglantine ;;
    3) python3 -u /userdata/system/lichii/update-emulators.py both ;;
    4) python3 -u /userdata/system/lichii/update-emulators.py lichii --rollback ;;
    5) python3 -u /userdata/system/lichii/update-emulators.py eglantine --rollback ;;
    6) python3 -u /userdata/system/lichii/update-emulators.py lichii-dlss ;;
    7) python3 -u /userdata/system/lichii/update-emulators.py lichii-dlss --rollback ;;
    *) exit 0 ;;
esac
printf '\n'
read -r -p 'Press Enter to close.' ignored
