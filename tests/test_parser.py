"""Tests for parser.py against an anonymised DeviceSignal response (schema 421).

Runs without Home Assistant installed: the parser and const modules are loaded
directly, bypassing the package __init__.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "thematronic"
FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> types.ModuleType:
    full = f"thematronic_under_test.{name}"
    spec = importlib.util.spec_from_file_location(full, PKG_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


pkg = types.ModuleType("thematronic_under_test")
pkg.__path__ = [str(PKG_DIR)]
sys.modules["thematronic_under_test"] = pkg
const = _load("const")
parser = _load("parser")

LOGIN_FORM = (
    '<form action="/de/sign/in/" method="post" class="pure-form" id="frm-signInForm">'
    '<div class="pure-control-group required"> <input type="hidden" name="_token_" '
    'value="dummyCsrfToken0123456789abcdef="> </div>'
    '<input type="email" name="username" id="frm-signInForm-username" required>'
    '<input type="password" name="password" id="frm-signInForm-password" required>'
    '<input type="submit" name="send" value="Einloggen">'
    '<input type="hidden" name="_do" value="signInForm-submit"></form>'
)


class ParserTest(unittest.TestCase):
    """Structure is a real portal response; the readings are made up."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.s = parser.parse_signals(
            json.loads((FIXTURES / "device_signal.json").read_text(encoding="utf-8"))
        )

    def test_login_token_and_device_id(self) -> None:
        self.assertEqual(
            parser.extract_login_token(LOGIN_FORM), "dummyCsrfToken0123456789abcdef="
        )
        self.assertIsNone(parser.extract_login_token("<html>nothing</html>"))
        html = '<span ng-init="lang=\'de\'"></span><span ng-init="deviceid=1234"></span>'
        self.assertEqual(parser.extract_device_ids(html), [1234])

    def test_boiler_1(self) -> None:
        self.assertEqual(parser.number(self.s, "s_t_spal"), 120.4)  # Abgastemperatur
        self.assertEqual(parser.number(self.s, "s_t_ko_vy"), 68.2)  # Kessel Vorlauf
        self.assertEqual(parser.number(self.s, "s_t_ko_vr"), 55.6)  # Kessel Rücklauf
        self.assertEqual(parser.iso_duration_to_hours(self.s["dev_horeni"].value), 0.0)
        self.assertFalse(parser.flag(self.s, "s_o_ko_vent"))
        self.assertTrue(parser.flag(self.s, "s_o_zd1_porucha"))
        self.assertTrue(parser.flag(self.s, "s_o_hav_term"))  # STB not tripped

    def test_missing_values_are_none(self) -> None:
        for key in ("s_t_nezamrz", "s_t_zona1", "s_t_aku2h", "s_t_tuv", "s_t_solar"):
            self.assertIsNone(parser.number(self.s, key), key)
        self.assertIsNone(parser.number(self.s, "s_o_zo1_vlhkost"))  # "---"
        self.assertIsNone(parser.blocking_difference(self.s, "s_o_blok_zbyva_z1"))
        self.assertIsNone(parser.number(self.s, "does_not_exist"))

    def test_outdoor_mode_buffer(self) -> None:
        self.assertEqual(parser.number(self.s, "s_t_venku"), -3.5)
        self.assertEqual(parser.season(self.s), "winter")
        self.assertEqual(parser.number(self.s, "s_t_akuh"), 64.0)
        self.assertEqual(parser.number(self.s, "s_t_akus"), 58.3)
        self.assertEqual(parser.number(self.s, "s_t_akud"), 41.7)

    def test_heating_circuits(self) -> None:
        self.assertEqual(parser.number(self.s, "s_t_zo1_vy"), 45.8)
        self.assertTrue(parser.flag(self.s, "s_o_zona_top"))
        self.assertEqual(parser.room_target_mode(self.s, 1), "comfort")
        self.assertEqual(parser.room_target_temperature(self.s, 1), 22.0)
        self.assertEqual(parser.room_target_mode(self.s, 2), "stop")
        self.assertIsNone(parser.room_target_temperature(self.s, 2))

    def test_hot_water(self) -> None:
        self.assertEqual(parser.dhw_target(self.s), "stop")  # page shows STOP
        self.assertIsNone(parser.dhw_target_temperature(self.s))

    def test_sections_for_schema_421(self) -> None:
        self.assertEqual(parser.schema_code(self.s), "421")
        self.assertEqual(
            parser.configured_sections("421"),
            {
                const.SECTION_BOILER_1,
                const.SECTION_OUTDOOR,
                const.SECTION_MODE,
                const.SECTION_HC_1,
                const.SECTION_HC_2,
                const.SECTION_BUFFER_1,
            },
        )
        self.assertIn(const.SECTION_SOLAR, parser.configured_sections(""))

    def test_durations(self) -> None:
        self.assertEqual(parser.iso_duration_to_hours("PT1H30M"), 1.5)
        self.assertEqual(parser.iso_duration_to_hours("P2DT3H"), 51.0)
        self.assertEqual(parser.iso_duration_to_hours("PT45S"), 0.013)
        self.assertIsNone(parser.iso_duration_to_hours("garbage"))
        self.assertIsNone(parser.iso_duration_to_hours(None))

    def test_bad_payload(self) -> None:
        with self.assertRaises(ValueError):
            parser.parse_signals({"ResponseStatus": {}})


if __name__ == "__main__":
    unittest.main()
