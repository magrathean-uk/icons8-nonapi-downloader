from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("icons8_pipeline", ROOT / "scripts" / "icons8_pipeline.py")
assert SPEC and SPEC.loader
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


def nuxt_html(payload: list[object]) -> str:
    return (
        '<html><body><script type="application/json" data-nuxt-data="nuxt-app" '
        f'data-ssr="true" id="__NUXT_DATA__">{json.dumps(payload)}</script></body></html>'
    )


class Icons8PageTests(unittest.TestCase):
    def test_extracts_every_icon_from_nuxt_payload_and_uses_url_slug(self) -> None:
        payload = [
            ["ShallowReactive", 1],
            {"data": 2},
            ["ShallowReactive", 3],
            {"search:/icons/set/business--style-glassmorphism": 4},
            {"categoryData": 5},
            {"category": 6},
            {"subcategory": 7},
            [8, 15],
            {"code": 9, "name": 10, "icons": 11},
            "business-communication",
            "Business Communication",
            [12],
            {
                "id": 13,
                "name": 14,
                "platform": 22,
                "url": 23,
                "commonName": 24,
            },
            "IPalISKXZCTQ",
            "Open email",
            {"code": 16, "name": 17, "icons": 18},
            "business-planning",
            "Business Planning",
            [19, 25],
            {
                "id": 20,
                "name": 21,
                "platform": 22,
                "url": 26,
                "commonName": 27,
            },
            "rdvHQ7vLfgGq",
            "Schedule",
            "glassmorphism",
            "/icon/IPalISKXZCTQ/open-email",
            "feedback",
            {
                "id": 28,
                "name": 29,
                "platform": 22,
                "url": 30,
                "commonName": 31,
            },
            "/icon/rdvHQ7vLfgGq/overtime",
            "overtime",
            "Z3STIRU4hxMn",
            "Briefcase",
            "/icon/Z3STIRU4hxMn/briefcase",
            "briefcase",
        ]
        rows = pipeline.extract_category_icons_from_html(
            nuxt_html(payload),
            "https://icons8.com/icons/set/business--style-glassmorphism",
        )

        self.assertEqual([row["icons8_id"] for row in rows], ["IPalISKXZCTQ", "rdvHQ7vLfgGq", "Z3STIRU4hxMn"])
        self.assertEqual(rows[0]["slug"], "open-email")
        self.assertEqual(rows[0]["common_name"], "feedback")
        self.assertEqual(rows[0]["asset_key"], "business--style-glassmorphism__open-email")
        self.assertEqual(rows[1]["subcategory_code"], "business-planning")

    def test_root_page_expansion_keeps_same_style_set_links(self) -> None:
        html = """
        <a href="/icons/set/business--style-glassmorphism">Business</a>
        <a href="https://icons8.com/icons/set/science--style-glassmorphism">Science</a>
        <a href="/icons/set/business--style-glassmorphism">Duplicate</a>
        <a href="/icons/set/business--style-fluency">Wrong style</a>
        """

        urls = pipeline.extract_set_page_urls(html, "https://icons8.com/icons/glassmorphism")

        self.assertEqual(
            urls,
            [
                "https://icons8.com/icons/set/business--style-glassmorphism",
                "https://icons8.com/icons/set/science--style-glassmorphism",
            ],
        )

    def test_extracts_icons_from_search_style_payload(self) -> None:
        payload = [
            ["ShallowReactive", 1],
            {"data": 2},
            ["ShallowReactive", 3],
            {"search:/icons/set/alphabet--style-glassmorphism": 4},
            {"iconsData": 5},
            {"icons": 6},
            [7],
            {
                "id": 8,
                "name": 9,
                "commonName": 10,
                "categoryApiCode": 11,
                "subcategory": 12,
                "platform": 13,
            },
            "DOlMmwoowTGs",
            "Alphabet",
            "abc",
            "baby",
            "Toys",
            "glassmorphism",
        ]

        rows = pipeline.extract_category_icons_from_html(
            nuxt_html(payload),
            "https://icons8.com/icons/set/alphabet--style-glassmorphism",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["asset_key"], "alphabet--style-glassmorphism__abc")
        self.assertEqual(rows[0]["subcategory_name"], "Toys")

    def test_output_filename_collisions_fail_before_download(self) -> None:
        rows = [
            {"asset_key": "business--style-glassmorphism__briefcase", "icons8_id": "one"},
            {"asset_key": "business--style-glassmorphism__briefcase", "icons8_id": "two"},
        ]

        with self.assertRaisesRegex(ValueError, "output collision"):
            pipeline.ensure_unique_asset_keys(rows)

    def test_disambiguates_real_page_slug_collisions_with_common_name(self) -> None:
        rows = [
            {
                "category": "popular",
                "style": "glassmorphism",
                "slug": "share",
                "common_name": "share--v2",
                "asset_key": "popular--style-glassmorphism__share",
                "icons8_id": "jIM732ayEMfP",
            },
            {
                "category": "popular",
                "style": "glassmorphism",
                "slug": "share",
                "common_name": "share--v1",
                "asset_key": "popular--style-glassmorphism__share",
                "icons8_id": "34ekiFycLzXv",
            },
        ]

        fixed = pipeline.disambiguate_asset_key_collisions(rows)

        self.assertEqual(
            [row["asset_key"] for row in fixed],
            [
                "popular--style-glassmorphism__share--v2",
                "popular--style-glassmorphism__share--v1",
            ],
        )


if __name__ == "__main__":
    unittest.main()
