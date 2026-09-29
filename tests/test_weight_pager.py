"""Tests for weight_pager (Wave 2A — partial load + streaming).

Changelog:
    25/09/2026 (Claude Code — Wave 2A): Initial.
"""
from __future__ import annotations

import unittest

from vivyqu.weight_pager import WeightPager, WeightSlice


class TestWeightSlice(unittest.TestCase):
    def test_byte_size(self) -> None:
        s = WeightSlice(alias="m", layer_range=(0, 2), format="gguf",
                        weights={"a": b"\x01\x02", "b": b"\x03"})
        self.assertEqual(s.byte_size, 3)

    def test_layer_count(self) -> None:
        s = WeightSlice(alias="m", layer_range=(0, 2), format="gguf",
                        weights={"a": b"x", "b": b"y"})
        self.assertEqual(s.layer_count, 2)

    def test_checksum_deterministic(self) -> None:
        w = {"l1": b"\x01", "l2": b"\x02"}
        s1 = WeightSlice(alias="m", layer_range=(0, 2), format="gguf", weights=dict(w))
        s2 = WeightSlice(alias="m", layer_range=(0, 2), format="gguf", weights=dict(w))
        self.assertEqual(s1.checksum, s2.checksum)

    def test_checksum_order_independent(self) -> None:
        s1 = WeightSlice(alias="m", layer_range=(0, 2), format="gguf",
                         weights={"a": b"\x01", "b": b"\x02"})
        s2 = WeightSlice(alias="m", layer_range=(0, 2), format="gguf",
                         weights={"b": b"\x02", "a": b"\x01"})
        self.assertEqual(s1.checksum, s2.checksum)

    def test_to_dict(self) -> None:
        s = WeightSlice(alias="m", layer_range=(0, 2), format="gguf",
                        weights={"a": b"\x01"})
        d = s.to_dict()
        self.assertEqual(d["alias"], "m")
        self.assertEqual(d["layer_count"], 1)


class TestWeightPagerRegister(unittest.TestCase):
    def test_register_and_get(self) -> None:
        wp = WeightPager()
        reg = wp.register_model("gemma4", "/models/gemma.gguf", "gguf",
                                total_layers=28)
        self.assertEqual(reg.alias, "gemma4")
        self.assertEqual(wp.model_count, 1)
        self.assertIsNotNone(wp.get_registration("gemma4"))

    def test_duplicate_alias_raises(self) -> None:
        wp = WeightPager()
        wp.register_model("m", "/p", "gguf")
        with self.assertRaises(ValueError):
            wp.register_model("m", "/p2", "gguf")

    def test_list_models(self) -> None:
        wp = WeightPager()
        wp.register_model("a", "/a", "gguf")
        wp.register_model("b", "/b", "gguf")
        self.assertEqual(wp.list_models(), ["a", "b"])


class TestWeightPagerLoadPartial(unittest.TestCase):
    def setUp(self) -> None:
        self.wp = WeightPager()
        self.wp.register_model("gemma4", "/models/gemma.gguf", "gguf",
                               total_layers=28)

    def test_load_partial_returns_slice(self) -> None:
        s = self.wp.load_partial("gemma4", (0, 4))
        self.assertEqual(s.layer_range, (0, 4))
        self.assertEqual(s.layer_count, 4)
        self.assertEqual(s.alias, "gemma4")

    def test_load_partial_deterministic(self) -> None:
        s1 = self.wp.load_partial("gemma4", (0, 2))
        s2 = self.wp.load_partial("gemma4", (0, 2))
        self.assertEqual(s1.checksum, s2.checksum)

    def test_load_unregistered_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.wp.load_partial("nope", (0, 1))

    def test_invalid_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.wp.load_partial("gemma4", (5, 3))
        with self.assertRaises(ValueError):
            self.wp.load_partial("gemma4", (-1, 3))

    def test_range_exceeds_layers_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.wp.load_partial("gemma4", (0, 100))

    def test_memory_usage_tracks(self) -> None:
        self.wp.load_partial("gemma4", (0, 4))
        mu = self.wp.memory_usage()
        self.assertEqual(mu["loaded_slices"], 1)
        self.assertGreater(mu["current_bytes"], 0)
        self.assertGreater(mu["peak_bytes"], 0)

    def test_clear_loaded(self) -> None:
        self.wp.load_partial("gemma4", (0, 4))
        self.wp.load_partial("gemma4", (4, 8))
        released = self.wp.clear_loaded()
        self.assertEqual(released, 2)
        self.assertEqual(self.wp.memory_usage()["loaded_slices"], 0)


class TestWeightPagerStream(unittest.TestCase):
    def setUp(self) -> None:
        self.wp = WeightPager()
        self.wp.register_model("gemma4", "/m.gguf", "gguf", total_layers=8)

    def test_stream_weights_calls_callback(self) -> None:
        collected: list[tuple[str, bytes]] = []
        n = self.wp.stream_weights(
            "gemma4", lambda key, data: collected.append((key, data))
        )
        self.assertEqual(n, 8)
        self.assertEqual(len(collected), 8)

    def test_iter_layers(self) -> None:
        layers = list(self.wp.iter_layers("gemma4"))
        self.assertEqual(len(layers), 8)

    def test_stream_unregistered_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.wp.stream_weights("nope", lambda k, d: None)

    def test_iter_unregistered_raises(self) -> None:
        with self.assertRaises(KeyError):
            list(self.wp.iter_layers("nope"))


if __name__ == "__main__":
    unittest.main()
