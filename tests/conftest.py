"""Stub out google.cloud.firestore before any test module imports it.

The google-cloud-firestore wheel requires native cffi/cryptography libraries that aren't
available in bare CI / lightweight containers. All tests that touch Firestore use
FakeStore monkeypatches anyway, so the real client is never called.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_firestore_stub() -> ModuleType:
    stub = ModuleType("google.cloud.firestore")
    stub.Client = MagicMock
    stub.SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
    stub.Increment = lambda n: n
    return stub


# Inject stubs before any src.* import can trigger the real package.
for name in (
    "google",
    "google.cloud",
    "google.cloud.firestore",
    "google.cloud.firestore_v1",
):
    if name not in sys.modules:
        sys.modules[name] = ModuleType(name)

sys.modules["google.cloud.firestore"] = _make_firestore_stub()
