"""Thin ctypes wrapper around the AEC3 C shim."""

from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import POINTER, c_float, c_int16, c_int, c_void_p


class AEC3:
    """Echo canceller using a small C shim.

    The shim exposes ``aec_init``, ``aec_process``, ``aec_erle`` and
    ``aec_free``. When the shared library is missing the class falls back to
    a pass-through that performs no echo cancellation.
    """

    def __init__(self, rate: int = 16000, frame: int = 320) -> None:
        self.rate = rate
        self.frame = frame
        libname = ctypes.util.find_library("aec3shim") or "./libaec3shim.so"
        try:
            self.lib = ctypes.CDLL(libname)
        except OSError:
            self.lib = None
            self.ctx = None
            return

        self.lib.aec_init.restype = c_void_p
        self.lib.aec_init.argtypes = [c_int, c_int]
        self.lib.aec_process.argtypes = [c_void_p, POINTER(c_int16), POINTER(c_int16), POINTER(c_int16)]
        self.lib.aec_erle.argtypes = [c_void_p]
        self.lib.aec_erle.restype = c_float
        self.lib.aec_free.argtypes = [c_void_p]
        self.ctx = c_void_p(self.lib.aec_init(rate, frame))

    def process(self, near_pcm: bytes, far_pcm: bytes) -> bytes:
        if self.ctx is None:
            return near_pcm
        near = (c_int16 * self.frame).from_buffer_copy(near_pcm)
        far = (c_int16 * self.frame).from_buffer_copy(far_pcm)
        out = (c_int16 * self.frame)()
        self.lib.aec_process(self.ctx, near, far, out)
        return bytes(out)

    def erle(self) -> float:
        if self.ctx is None:
            return 0.0
        return float(self.lib.aec_erle(self.ctx))

    def close(self) -> None:
        if self.ctx is not None:
            self.lib.aec_free(self.ctx)
            self.ctx = None
