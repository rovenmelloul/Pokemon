"""SoundManager -- Gestionnaire audio pour le jeu Pokemon 3D.
Musique de fond (loop) + effets sonores (SFX) par type d'attaque, pokeball, UI, etc.
Utilise le systeme audio natif de Panda3D.
"""
import os
from panda3d.core import Filename

_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio")
_SFX_DIR = os.path.join(_AUDIO_DIR, "sfx")
_MUSIC_DIR = os.path.join(_AUDIO_DIR, "music")


class SoundManager:
    """Centralized audio manager.

    Usage:
        sm = SoundManager(base)
        sm.play_music("menu_theme")
        sm.play_sfx("hit")
        sm.play_attack_sfx("fire")
    """

    def __init__(self, base):
        self._base = base
        self._music_volume = 0.4
        self._sfx_volume = 0.6
        self._current_music = None
        self._current_music_name = None
        self._sfx_cache = {}
        self._music_cache = {}

    # ------------------------------------------------------------------
    # Volume controls
    # ------------------------------------------------------------------

    @property
    def music_volume(self):
        return self._music_volume

    @music_volume.setter
    def music_volume(self, value):
        self._music_volume = max(0.0, min(1.0, value))
        if self._current_music:
            self._current_music.setVolume(self._music_volume)

    @property
    def sfx_volume(self):
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value):
        self._sfx_volume = max(0.0, min(1.0, value))

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------

    def play_music(self, name, loop=True):
        """Play a music track from audio/music/<name>.wav.
        Stops any currently playing music first.
        """
        if self._current_music_name == name and self._current_music:
            if self._current_music.status() == self._current_music.PLAYING:
                return  # Already playing
        self.stop_music()

        sound = self._load_music(name)
        if not sound:
            return

        sound.setLoop(loop)
        sound.setVolume(self._music_volume)
        sound.play()
        self._current_music = sound
        self._current_music_name = name

    def stop_music(self):
        """Stop the current music."""
        if self._current_music:
            self._current_music.stop()
            self._current_music = None
            self._current_music_name = None

    def fade_music(self, target_volume=0.0, duration=1.0):
        """Fade current music to target volume over duration seconds."""
        if not self._current_music:
            return

        music = self._current_music
        start_vol = music.getVolume()
        steps = int(duration * 30)  # 30 steps per second

        if steps <= 0:
            music.setVolume(target_volume)
            if target_volume <= 0:
                self.stop_music()
            return

        step_size = (target_volume - start_vol) / steps
        step_time = duration / steps

        def fade_step(task, step=[0]):
            step[0] += 1
            new_vol = start_vol + step_size * step[0]
            new_vol = max(0.0, min(1.0, new_vol))
            if music.status() != music.PLAYING:
                return task.done
            music.setVolume(new_vol)
            if step[0] >= steps:
                if target_volume <= 0:
                    self.stop_music()
                return task.done
            return task.again

        self._base.taskMgr.doMethodLater(
            step_time, fade_step, "music_fade"
        )

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------

    def play_sfx(self, name, volume=None):
        """Play a sound effect from audio/sfx/<name>.wav."""
        sound = self._load_sfx(name)
        if not sound:
            return None
        vol = volume if volume is not None else self._sfx_volume
        sound.setVolume(vol)
        sound.play()
        return sound

    def play_attack_sfx(self, attack_type):
        """Play the attack sound for a given Pokemon type."""
        type_lower = attack_type.lower() if attack_type else "normal"
        return self.play_sfx(f"attack_{type_lower}")

    # ------------------------------------------------------------------
    # Loader helpers
    # ------------------------------------------------------------------

    def _load_sfx(self, name):
        """Load (and cache) a sound effect."""
        if name in self._sfx_cache:
            return self._sfx_cache[name]

        path = os.path.join(_SFX_DIR, f"{name}.wav")
        if not os.path.exists(path):
            return None

        try:
            sound = self._base.loader.loadSfx(
                Filename.fromOsSpecific(path)
            )
            self._sfx_cache[name] = sound
            return sound
        except Exception as e:
            print(f"[Sound] Error loading SFX {name}: {e}")
            return None

    def _load_music(self, name):
        """Load a music track (not cached - each call gets a new instance)."""
        if name in self._music_cache:
            return self._music_cache[name]

        path = os.path.join(_MUSIC_DIR, f"{name}.wav")
        if not os.path.exists(path):
            return None

        try:
            sound = self._base.loader.loadMusic(
                Filename.fromOsSpecific(path)
            )
            self._music_cache[name] = sound
            return sound
        except Exception as e:
            print(f"[Sound] Error loading music {name}: {e}")
            return None

    def destroy(self):
        """Clean up all audio."""
        self.stop_music()
        self._sfx_cache.clear()
        self._music_cache.clear()
