"""Weight Pager Interface — Partial load + streaming for multi-model cores (TD-4).

Provides an interface over the C-ABI GGUF weight pager to load only the
weight slices needed for a given task, without loading the full model.
Supports Q4_K / Q6_K quantization formats.

Structure:
    WeightPager
    ├── register_model(alias, path, format) — register a model core
    ├── load_partial(alias, layer_range) -> WeightSlice — load specific layers
    ├── stream_weights(alias, callback) — stream weights in chunks
    └── memory_usage() -> dict — current memory footprint

    WeightSlice (frozen dataclass)
    ├── alias, layer_range, format
    ├── weights: dict[str, bytes] (layer_id -> raw tensor bytes)
    └── byte_size, metadata

Partial load enables Vivy to inspect/use weights from large models (e.g.
Qwen2-VL-72B) without full RAM residency. Stream mode feeds callbacks
per-layer for out-of-core processing.

Changelog:
    25/09/2026 (Claude Code — Wave 2A): Initial.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WeightSlice:
    """A partial view of model weights covering a layer range."""

    alias: str
    layer_range: tuple[int, int]
    format: str
    weights: dict[str, bytes] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def byte_size(self) -> int:
        return sum(len(v) for v in self.weights.values())

    @property
    def layer_count(self) -> int:
        return len(self.weights)

    @property
    def checksum(self) -> str:
        """SHA256 over all layer bytes (deterministic ordering)."""
        h = hashlib.sha256()
        for key in sorted(self.weights):
            h.update(key.encode("utf-8"))
            h.update(self.weights[key])
        return h.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "layer_range": list(self.layer_range),
            "format": self.format,
            "layer_count": self.layer_count,
            "byte_size": self.byte_size,
            "checksum": self.checksum,
            "metadata": dict(self.metadata),
        }


@dataclass
class ModelRegistration:
    """Registration record for a model core."""

    alias: str
    path: str
    format: str
    total_layers: int = 0
    total_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class WeightPager:
    """Interface over partial weight loading for registered model cores.

    Wraps the C-ABI GGUF weight pager conceptually: each model is registered
    once, then weight slices can be loaded or streamed on demand. The actual
    byte data is simulated via deterministic content derivation (real pager
    would read from GGUF mmap). This is the orchestration-level interface
    that CrossModelAdapter (TD-5) consumes.
    """

    def __init__(self) -> None:
        self._registry: dict[str, ModelRegistration] = {}
        self._loaded_slices: list[WeightSlice] = []
        self._peak_bytes: int = 0

    @property
    def model_count(self) -> int:
        return len(self._registry)

    def register_model(
        self,
        alias: str,
        path: str,
        format: str = "gguf",
        *,
        total_layers: int = 0,
        total_bytes: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ModelRegistration:
        """Register a model core for partial weight access.

        Raises ValueError if alias already registered (isolate-not-delete:
        re-registration requires a different alias).
        """
        if alias in self._registry:
            raise ValueError(f"model alias already registered: {alias}")
        reg = ModelRegistration(
            alias=alias,
            path=path,
            format=format,
            total_layers=total_layers,
            total_bytes=total_bytes,
            metadata=dict(metadata or {}),
        )
        self._registry[alias] = reg
        return reg

    def get_registration(self, alias: str) -> ModelRegistration | None:
        return self._registry.get(alias)

    def list_models(self) -> list[str]:
        return sorted(self._registry)

    def load_partial(
        self, alias: str, layer_range: tuple[int, int]
    ) -> WeightSlice:
        """Load a slice of weights covering [start, end) layers.

        Returns a WeightSlice with simulated tensor bytes derived from
        (alias, layer_index) for deterministic testing.

        Raises KeyError if alias not registered.
        Raises ValueError if layer_range is invalid.
        """
        if alias not in self._registry:
            raise KeyError(f"model not registered: {alias}")
        start, end = layer_range
        if start < 0 or end < start:
            raise ValueError(f"invalid layer_range: {layer_range}")

        reg = self._registry[alias]
        if reg.total_layers > 0 and end > reg.total_layers:
            raise ValueError(
                f"layer_range {layer_range} exceeds total_layers={reg.total_layers}"
            )

        weights: dict[str, bytes] = {}
        for layer_idx in range(start, end):
            key = f"layer_{layer_idx:04d}"
            # Deterministic pseudo-tensor bytes for testing.
            seed = f"{alias}:{layer_idx}".encode()
            weights[key] = hashlib.sha256(seed).digest()

        slice_ = WeightSlice(
            alias=alias,
            layer_range=(start, end),
            format=reg.format,
            weights=weights,
            metadata={"path": reg.path},
        )
        self._loaded_slices.append(slice_)
        current = self.total_loaded_bytes
        self._peak_bytes = max(self._peak_bytes, current)
        return slice_

    def stream_weights(
        self, alias: str, callback: Callable[[str, bytes], None]
    ) -> int:
        """Stream all registered layers of a model through a callback.

        The callback receives (layer_key, tensor_bytes) per layer. Returns
        the number of layers streamed.

        Raises KeyError if alias not registered.
        """
        if alias not in self._registry:
            raise KeyError(f"model not registered: {alias}")
        reg = self._registry[alias]
        n_layers = reg.total_layers if reg.total_layers > 0 else 16
        for layer_idx in range(n_layers):
            key = f"layer_{layer_idx:04d}"
            seed = f"{alias}:{layer_idx}".encode()
            callback(key, hashlib.sha256(seed).digest())
        return n_layers

    def iter_layers(self, alias: str) -> Iterator[tuple[str, bytes]]:
        """Iterate layers of a registered model (generator form)."""
        if alias not in self._registry:
            raise KeyError(f"model not registered: {alias}")
        reg = self._registry[alias]
        n_layers = reg.total_layers if reg.total_layers > 0 else 16
        for layer_idx in range(n_layers):
            key = f"layer_{layer_idx:04d}"
            seed = f"{alias}:{layer_idx}".encode()
            yield key, hashlib.sha256(seed).digest()

    @property
    def total_loaded_bytes(self) -> int:
        return sum(s.byte_size for s in self._loaded_slices)

    @property
    def peak_bytes(self) -> int:
        return self._peak_bytes

    def memory_usage(self) -> dict[str, Any]:
        """Report current and peak memory footprint of loaded slices."""
        return {
            "loaded_slices": len(self._loaded_slices),
            "current_bytes": self.total_loaded_bytes,
            "peak_bytes": self._peak_bytes,
            "models_registered": len(self._registry),
        }

    def clear_loaded(self) -> int:
        """Release all loaded slices. Returns count released."""
        n = len(self._loaded_slices)
        self._loaded_slices.clear()
        return n
