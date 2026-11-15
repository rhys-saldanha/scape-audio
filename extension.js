import Gio from 'gi://Gio';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class ScapeAudioExtension extends Extension {
    enable() {
        this._proc = Gio.Subprocess.new(
            ['python3', `${this.path}/scape_audio.py`], Gio.SubprocessFlags.NONE);
    }

    disable() {
        this._proc?.force_exit();
        this._proc = null;
    }
}
