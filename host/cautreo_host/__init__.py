"""cautreo_host — host mảnh cho Cautreo Desktop UI.

Đúng ba thứ (spec §3): cửa sổ · Plugin Registry · IPC Bus.
Host **không biết** ViVy là gì, Cautreo là gì, model là gì — đó là việc của plugin.
"""

from __future__ import annotations

from .bus import (
    INVALID_REQUEST,
    MODEL_UNAVAILABLE,
    PARSE_ERROR,
    PERMISSION_DENIED,
    PLUGIN_ERROR,
    PLUGIN_RELOADING,
    PLUGIN_UNAVAILABLE,
    Bus,
    MethodSpec,
)
from .manifest import (
    SUPPORTED_API,
    ContractError,
    Manifest,
    parse_manifest,
    parse_manifest_dict,
)
from .provenance import (
    ALL_SOURCES,
    SOURCE_CAUTREO,
    SOURCE_DERIVED,
    SOURCE_MODEL,
    SOURCE_TOOL_LOCAL,
    CallContext,
    Capability,
    PermissionDenied,
    source_for,
    strip_self_label,
)
from .receipt import Receipt, ReceiptError, ReceiptLog
from .backends import CautreoMemoryBackend
from .backends import CautreoMemoryBackend
from .registry import (
    PluginRecord,
    PluginRegistry,
    PluginReloading,
    PluginState,
    RegistryError,
)
from .state import REASONS, LinkError, LinkMachine, LinkState

__all__ = [
    "ALL_SOURCES",
    "INVALID_REQUEST",
    "MODEL_UNAVAILABLE",
    "PARSE_ERROR",
    "PERMISSION_DENIED",
    "PLUGIN_ERROR",
    "PLUGIN_RELOADING",
    "PLUGIN_UNAVAILABLE",
    "REASONS",
    "SUPPORTED_API",
    "SOURCE_CAUTREO",
    "SOURCE_DERIVED",
    "SOURCE_MODEL",
    "SOURCE_TOOL_LOCAL",
    "Bus",
    "CallContext",
    "Capability",
    "CautreoMemoryBackend",
    "ContractError",
    "LinkError",
    "LinkMachine",
    "LinkState",
    "Manifest",
    "MethodSpec",
    "PermissionDenied",
    "PluginRecord",
    "PluginRegistry",
    "PluginReloading",
    "PluginState",
    "Receipt",
    "ReceiptError",
    "ReceiptLog",
    "RegistryError",
    "parse_manifest",
    "parse_manifest_dict",
    "source_for",
    "strip_self_label",
]

__version__ = "0.1.0"
