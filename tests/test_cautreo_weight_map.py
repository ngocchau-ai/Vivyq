"""Tests for cautreo_weight_map (Wave 1A — tree index).

Changelog:
    25/09/2026 (Claude Code — Wave 1A): Initial.
"""
from __future__ import annotations

import unittest

from vivyqu.cautreo_weight_map import (
    WeightMap,
    WeightNode,
    build_default_weight_map,
)


class TestWeightNode(unittest.TestCase):
    def test_is_leaf(self) -> None:
        n = WeightNode(node_id="a", model_alias="m")
        self.assertTrue(n.is_leaf())

    def test_not_leaf_with_children(self) -> None:
        n = WeightNode(node_id="a", model_alias="m", children=["b"])
        self.assertFalse(n.is_leaf())

    def test_to_dict(self) -> None:
        n = WeightNode(
            node_id="a", model_alias="m", layer_range=(0, 10),
            capability_tags=("t1",), score=0.8,
        )
        d = n.to_dict()
        self.assertEqual(d["node_id"], "a")
        self.assertEqual(d["layer_range"], [0, 10])
        self.assertEqual(d["capability_tags"], ["t1"])
        self.assertEqual(d["score"], 0.8)


class TestWeightMapInsert(unittest.TestCase):
    def test_insert_and_get(self) -> None:
        wm = WeightMap()
        wm.insert(WeightNode(node_id="n1", model_alias="m1"))
        self.assertEqual(wm.size, 1)
        self.assertIsNotNone(wm.get("n1"))

    def test_insert_links_parent(self) -> None:
        wm = WeightMap()
        wm.insert(WeightNode(node_id="parent", model_alias="m"))
        wm.insert(WeightNode(node_id="child", model_alias="m", parent_id="parent"))
        parent = wm.get("parent")
        assert parent is not None
        self.assertIn("child", parent.children)

    def test_insert_indexes_capability(self) -> None:
        wm = WeightMap()
        wm.insert(WeightNode(node_id="n1", model_alias="m", capability_tags=("code",)))
        results = wm.by_capability("code")
        self.assertEqual(len(results), 1)


class TestWeightMapLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.wm = build_default_weight_map()

    def test_lookup_by_node_id_prefix(self) -> None:
        results = self.wm.lookup("gemma4")
        self.assertGreaterEqual(len(results), 2)

    def test_lookup_by_model_alias(self) -> None:
        results = self.wm.lookup("qwen2-70b")
        self.assertEqual(len(results), 1)

    def test_lookup_by_capability_tag(self) -> None:
        results = self.wm.lookup("code")
        self.assertEqual(len(results), 1)

    def test_lookup_no_match(self) -> None:
        results = self.wm.lookup("nonexistent")
        self.assertEqual(len(results), 0)


class TestWeightMapByCapability(unittest.TestCase):
    def setUp(self) -> None:
        self.wm = build_default_weight_map()

    def test_sorted_by_score(self) -> None:
        results = self.wm.by_capability("general")
        self.assertGreater(len(results), 0)
        scores = [n.score for n in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_capability(self) -> None:
        results = self.wm.by_capability("nonexistent")
        self.assertEqual(results, [])


class TestWeightMapTree(unittest.TestCase):
    def setUp(self) -> None:
        self.wm = build_default_weight_map()

    def test_children_of(self) -> None:
        children = self.wm.children_of("root")
        self.assertGreater(len(children), 0)

    def test_children_of_missing(self) -> None:
        self.assertEqual(self.wm.children_of("nope"), [])

    def test_path_to_root(self) -> None:
        path = self.wm.path_to_root("gemma4-memory")
        self.assertGreater(len(path), 1)
        self.assertEqual(path[-1].node_id, "root")

    def test_path_to_root_leaf(self) -> None:
        path = self.wm.path_to_root("root")
        self.assertEqual(len(path), 1)


class TestWeightMapScore(unittest.TestCase):
    def test_update_score(self) -> None:
        wm = build_default_weight_map()
        wm.update_score("gemma4-general", 0.95)
        node = wm.get("gemma4-general")
        assert node is not None
        self.assertAlmostEqual(node.score, 0.95)

    def test_update_score_clamped(self) -> None:
        wm = build_default_weight_map()
        wm.update_score("gemma4-general", 1.5)
        node = wm.get("gemma4-general")
        assert node is not None
        self.assertAlmostEqual(node.score, 1.0)
        wm.update_score("gemma4-general", -0.5)
        assert node is not None
        self.assertAlmostEqual(node.score, 0.0)

    def test_update_missing_raises(self) -> None:
        wm = WeightMap()
        with self.assertRaises(KeyError):
            wm.update_score("nope", 0.5)


class TestWeightMapSerialization(unittest.TestCase):
    def test_round_trip(self) -> None:
        wm = build_default_weight_map()
        d = wm.to_dict()
        wm2 = WeightMap.from_dict(d)
        self.assertEqual(wm2.size, wm.size)
        self.assertEqual(len(wm2.by_capability("code")), len(wm.by_capability("code")))

    def test_empty_round_trip(self) -> None:
        wm = WeightMap()
        wm2 = WeightMap.from_dict(wm.to_dict())
        self.assertEqual(wm2.size, 0)


class TestDefaultWeightMap(unittest.TestCase):
    def test_has_known_models(self) -> None:
        wm = build_default_weight_map()
        self.assertIsNotNone(wm.get("gemma4-general"))
        self.assertIsNotNone(wm.get("qwen-70b-specialized"))

    def test_capability_tags(self) -> None:
        wm = build_default_weight_map()
        self.assertGreater(len(wm.by_capability("reasoning")), 0)
        self.assertGreater(len(wm.by_capability("code")), 0)


if __name__ == "__main__":
    unittest.main()
