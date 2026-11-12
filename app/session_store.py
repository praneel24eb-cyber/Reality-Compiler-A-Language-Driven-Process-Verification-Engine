"""User-bound Windows DPAPI storage. No plaintext credential fallback."""

import ctypes
import json
import os
from contextlib import contextmanager
from pathlib import Path


def protect(data: bytes, *, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise OSError("Persistent ChatGPT sessions require Windows DPAPI on this installation")
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]

    buffer = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)  # type: ignore[attr-defined]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    # UI_FORBIDDEN, with current-user protection (never LOCAL_MACHINE).
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise OSError("Windows could not protect or restore the session")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        self.enabled = os.name == "nt"

    @contextmanager
    def locked(self):
        """Serialize rotating tokens across local backend processes."""
        if not self.enabled:
            yield
            return
        import msvcrt  # type: ignore[import-not-found]

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+b") as lock:
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]

    def load(self) -> dict:
        if not self.enabled or not self.path.exists():
            return {}
        try:
            data = json.loads(protect(self.path.read_bytes(), decrypt=True))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, data: dict) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = protect(json.dumps(data).encode("utf-8"))
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        temporary.replace(self.path)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
