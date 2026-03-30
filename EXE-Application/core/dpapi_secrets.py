"""Secret protection helpers with Windows DPAPI as the primary backend.

On Windows, secret bytes are encrypted/decrypted using CryptProtectData and
CryptUnprotectData. Resulting blobs are tied to the local machine and user
context under normal DPAPI semantics.

On non-Windows platforms, this module falls back to in-memory encryption to
keep the application operational in development and test environments.
"""

import ctypes
import ctypes.wintypes
import os
import platform
import struct
import threading
from typing import Optional

_IS_WINDOWS = platform.system() == "Windows"

# Windows DPAPI implementation

if _IS_WINDOWS:
    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    def _to_blob(data: bytes) -> _DATA_BLOB:
        blob = _DATA_BLOB()
        blob.cbData = len(data)
        blob.pbData = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        return blob

    def _from_blob(blob: "_DATA_BLOB") -> bytes:
        return bytes(blob.pbData[:blob.cbData])

    def protect(plaintext: bytes, description: str = "ObserveProctor") -> bytes:
        """
        Encrypt plaintext with Windows DPAPI.

        Args:
            plaintext: Raw secret bytes.
            description: Optional DPAPI description string.

        Returns:
            Opaque encrypted blob suitable for storage.

        Raises:
            RuntimeError: If CryptProtectData fails.
        """
        data_in   = _to_blob(plaintext)
        data_out  = _DATA_BLOB()
        desc      = ctypes.c_wchar_p(description)

        ok = _crypt32.CryptProtectData(
            ctypes.byref(data_in),
            desc,
            None,   # optional entropy
            None,   # reserved
            None,   # no prompt
            0,      # flags
            ctypes.byref(data_out),
        )
        if not ok:
            raise RuntimeError(f"CryptProtectData failed: {_kernel32.GetLastError()}")

        result = _from_blob(data_out)
        _kernel32.LocalFree(data_out.pbData)
        return result

    def unprotect(ciphertext: bytes) -> bytes:
        """
        Decrypt a DPAPI-protected blob.

        Args:
            ciphertext: Opaque encrypted blob previously returned by protect.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            RuntimeError: If CryptUnprotectData fails.
        """
        data_in  = _to_blob(ciphertext)
        data_out = _DATA_BLOB()

        ok = _crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,   # description out (ignored)
            None,   # optional entropy
            None,   # reserved
            None,   # no prompt
            0,      # flags
            ctypes.byref(data_out),
        )
        if not ok:
            raise RuntimeError(f"CryptUnprotectData failed: {_kernel32.GetLastError()}")

        result = _from_blob(data_out)
        _kernel32.LocalFree(data_out.pbData)
        return result

else:
    # Non-Windows fallback path.
    _fallback_key = os.urandom(32)

    def protect(plaintext: bytes, description: str = "") -> bytes:
        """Encrypt data using a per-session fallback key.

        Preferred fallback is AES-256-GCM when cryptography is available.
        If cryptography is missing, a weak XOR fallback is used to avoid
        crashing; it should not be considered secure storage.
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = os.urandom(12)
            ct    = AESGCM(_fallback_key).encrypt(nonce, plaintext, None)
            return nonce + ct
        except ImportError:
            # Last-resort compatibility fallback for environments without cryptography.
            print("[DPAPI] WARNING: cryptography not installed — using XOR fallback (insecure).")
            key_rep = (_fallback_key * (len(plaintext) // 32 + 1))[:len(plaintext)]
            return bytes(a ^ b for a, b in zip(plaintext, key_rep))

    def unprotect(ciphertext: bytes) -> bytes:
        """Decrypt data produced by the non-Windows fallback implementation."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce, ct = ciphertext[:12], ciphertext[12:]
            return AESGCM(_fallback_key).decrypt(nonce, ct, None)
        except ImportError:
            key_rep = (_fallback_key * (len(ciphertext) // 32 + 1))[:len(ciphertext)]
            return bytes(a ^ b for a, b in zip(ciphertext, key_rep))


# Convenience wrappers for UTF-8 strings

def protect_str(secret: str) -> bytes:
    """Encode a string as UTF-8 and protect it as bytes."""
    return protect(secret.encode("utf-8"))

def unprotect_str(blob: bytes) -> str:
    """Unprotect bytes and decode them from UTF-8."""
    return unprotect(blob).decode("utf-8")


# In-memory named secret registry

class SecretStore:
    """
    Thread-safe named secret store backed by protect/unprotect.

    Stored values are encrypted blobs in memory. Plaintext is reconstructed
    only when get() is called.
    """

    def __init__(self):
        self._store: dict[str, bytes] = {}   # name -> protected blob
        self._lock = threading.RLock()

    def set(self, name: str, value: bytes) -> None:
        """Encrypt and store a secret."""
        with self._lock:
            self._store[name] = protect(value)

    def get(self, name: str) -> Optional[bytes]:
        """Decrypt and return a secret, or None if not found."""
        with self._lock:
            blob = self._store.get(name)
        if blob is None:
            return None
        try:
            return unprotect(blob)
        except Exception as e:
            print(f"[SecretStore] Failed to unprotect '{name}': {e}")
            return None

    def delete(self, name: str) -> None:
        """Remove a secret."""
        with self._lock:
            self._store.pop(name, None)

    def wipe(self) -> None:
        """Clear all stored blobs from memory."""
        with self._lock:
            self._store.clear()
