#!/bin/bash
set -eu

common_dir=/userdata/system/lichii
emulator=lichii
if [[ ${1:-} == --emulator ]]; then
    emulator=${2:-lichii}
    shift 2
fi
case "$emulator" in
    lichii) app_dir="$common_dir"; config_name=eden; window_name=Lichii ;;
    eglantine) app_dir=/userdata/system/eglantine; config_name=eglantine; window_name=Eglantine ;;
    lichii-dlss) app_dir=/userdata/system/lichii-dlss; config_name=lichii; window_name=Lichii ;;
    *) printf 'Unknown Switch 2 emulator: %s\n' "$emulator" >&2; exit 2 ;;
esac
app="$app_dir/current.AppImage"
rom_dir=/userdata/roms/switch2

export XDG_CONFIG_HOME="$app_dir/profile/config"
export XDG_DATA_HOME="$app_dir/profile/data"
export XDG_CACHE_HOME="$app_dir/profile/cache"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/lichii-switch2}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
case "${LC_ALL:-${LC_CTYPE:-${LANG:-C}}}" in
    C|POSIX|C.UTF-8) export LC_ALL=en_US.UTF-8 ;;
esac
install -d -m 700 "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
cd "$app_dir"

exec {lock_fd}>"$common_dir/profile/launch.lock"
if ! flock -n "$lock_fd"; then
    if [[ ${1:-} == --settings ]]; then
        wmctrl -a "$window_name" || true
        exit 0
    fi
    printf 'Close the open Switch 2 emulator before launching another game.\n' >&2
    exit 1
fi

# Build 150 introduced a separate Lichii profile. Older builds still use Eden.
if [[ "$emulator" == lichii ]]; then
    app_file=$(basename "$(readlink -f "$app")")
    if [[ "$app_file" =~ ^lichii-build-([0-9]+)[.-] ]] && (( 10#${BASH_REMATCH[1]} >= 150 )); then
        config_name=lichii
    fi
fi
config_file="$XDG_CONFIG_HOME/$config_name/qt-config.ini"
python3 "$common_dir/sync-library.py" "$config_file"
controller_family="$emulator"
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
python3 /userdata/system/streaming-control/switch2-session.py "$controller_family" "$config_file"
# Use the same default audio device as Batocera and Sunshine.
export SDL_AUDIO_DRIVER=pulseaudio
export SDL_AUDIODRIVER=pulseaudio

case "${1:-}" in
    --settings)
        "$app" {lock_fd}>&-
        exit
        ;;
    "$rom_dir/"*) rom="$1" ;;
    *) printf 'The emulator expects a game in %s\n' "$rom_dir" >&2; exit 2 ;;
esac

if [[ -d "$rom" ]]; then
    if [[ -f "$rom/exefs/main" && -f "$rom/exefs/main.npdm" ]]; then
        rom="$rom/exefs/main"
    elif [[ -f "$rom/base/exefs/main" && -f "$rom/base/exefs/main.npdm" ]]; then
        rom="$rom/base/exefs/main"
    else
        printf 'Cannot find exefs/main and main.npdm in %s\n' "$rom" >&2
        exit 2
    fi
fi
if [[ ! -f "$rom" ]]; then
    printf 'Game file is missing: %s\n' "$rom" >&2
    exit 2
fi

cursor_shown=false
hotkeys_set=false
python3 /userdata/system/emulators/ensure-hotkeys.py
cleanup() {
    if "$hotkeys_set"; then
        hotkeygen --default-context >/dev/null 2>&1 || true
    fi
    if "$cursor_shown"; then
        batocera-mouse hide >/dev/null 2>&1 || true
    fi
    sync_shared_controls_back
}
trap cleanup EXIT

if batocera-mouse show; then
    cursor_shown=true
fi
if command -v hotkeygen >/dev/null && hotkeygen --new-context "$emulator" '{"exit":["KEY_LEFTALT","KEY_F4"]}'; then
    hotkeys_set=true
fi
"$app" -f -g "$rom" {lock_fd}>&- &
app_pid=$!
python3 "$common_dir/exit-watch.py" "$app_pid" "$XDG_DATA_HOME/$config_name/log/eden_log.txt" {lock_fd}>&- &
watch_pid=$!
status=0
wait "$app_pid" || status=$?
kill "$watch_pid" 2>/dev/null || true
wait "$watch_pid" 2>/dev/null || true
exit "$status"
