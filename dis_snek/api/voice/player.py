import asyncio
import logging
import shutil
import threading
import time
from asyncio import AbstractEventLoop
from typing import Optional, TYPE_CHECKING

from dis_snek.client.const import logger_name
from dis_snek.api.voice.audio import BaseAudio, AudioVolume
from dis_snek.api.voice.opus import Encoder

if TYPE_CHECKING:
    from dis_snek.models.snek.active_voice_state import ActiveVoiceState
__all__ = ("Player",)

log = logging.getLogger(logger_name)


class Player(threading.Thread):
    def __init__(self, audio, v_state, loop) -> None:
        super().__init__()
        self.daemon = True

        self.current_audio: Optional[BaseAudio] = audio
        self.state: "ActiveVoiceState" = v_state
        self.loop: AbstractEventLoop = loop

        self._encoder: Encoder = Encoder()

        self._resume: threading.Event = threading.Event()

        self._stop_event: threading.Event = threading.Event()
        self._stopped: asyncio.Event = asyncio.Event()

        self._sent_payloads: int = 0

        self._cond = threading.Condition()

        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "Unable to start player. FFmpeg was not found. Please add it to your project directory or PATH. (https://ffmpeg.org/)"
            )

    def __enter__(self) -> "Player":
        self.state.ws.cond = self._cond
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            self.state.ws.cond = None
        except AttributeError:
            pass

    def stop(self) -> None:
        """Stop playing completely."""
        self._stop_event.set()
        with self._cond:
            self._cond.notify()

    def resume(self) -> None:
        """Resume playing."""
        self._resume.set()
        with self._cond:
            self._cond.notify()

    @property
    def paused(self) -> bool:
        """Is the player paused"""
        return not self._resume.is_set()

    def pause(self) -> None:
        """Pause the player."""
        self._resume.clear()

    @property
    def stopped(self) -> bool:
        """Is the player currently stopped?"""
        return self._stopped.is_set()

    @property
    def elapsed_time(self) -> float:
        """How many seconds of audio the player has sent."""
        return self._sent_payloads * self._encoder.delay

    def play(self) -> None:
        """Start playing."""
        self._stop_event.clear()
        self._resume.set()
        try:
            self.start()
        finally:
            self.current_audio.cleanup()

    def run(self) -> None:
        """The main player loop to send audio to the voice websocket."""
        loops = 0

        if isinstance(self.current_audio, AudioVolume):
            # noinspection PyProtectedMember
            self.current_audio.volume = self.state._volume

        self._encoder.set_bitrate(getattr(self.current_audio, "bitrate", self.state.channel.bitrate))

        self._stopped.clear()

        asyncio.run_coroutine_threadsafe(self.state.ws.speaking(True), self.loop)
        log.debug(f"Now playing {self.current_audio!r}")
        start = None

        try:
            while not self._stop_event.is_set():
                if not self.state.ws.ready.is_set() or not self._resume.is_set():
                    asyncio.run_coroutine_threadsafe(self.state.ws.speaking(False), self.loop)
                    log.debug("Voice playback has been suspended!")

                    wait_for = []

                    if not self.state.ws.ready.is_set():
                        wait_for.append(self.state.ws.ready)
                    if not self._resume.is_set():
                        wait_for.append(self._resume)

                    with self._cond:
                        while not (self._stop_event.is_set() or all(x.is_set() for x in wait_for)):
                            self._cond.wait()
                    if self._stop_event.is_set():
                        continue

                    asyncio.run_coroutine_threadsafe(self.state.ws.speaking(), self.loop)
                    log.debug("Voice playback has been resumed!")
                    start = None
                    loops = 0

                if data := self.current_audio.read(self._encoder.frame_size):
                    self.state.ws.send_packet(data, self._encoder, needs_encode=self.current_audio.needs_encode)
                else:
                    if self.current_audio.locked_stream or not self.current_audio.audio_complete:
                        # if more audio is expected
                        self.state.ws.send_packet(b"\xF8\xFF\xFE", self._encoder, needs_encode=False)
                    else:
                        break

                if not start:
                    start = time.perf_counter()

                loops += 1
                self._sent_payloads += 1  # used for duration calc
                time.sleep(max(0.0, start + (self._encoder.delay * loops) - time.perf_counter()))
        finally:
            asyncio.run_coroutine_threadsafe(self.state.ws.speaking(False), self.loop)
            self.current_audio.cleanup()
            self.loop.call_soon_threadsafe(self._stopped.set)
