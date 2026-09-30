from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication

from core.building import (
    BUILDING_PRESETS,
    CHILD,
    FEMALE,
    MALE,
    OFFICE,
    PEOPLE_KINDS,
    RESIDENTIAL,
    WHEELCHAIR,
    Building,
)
from core.profiles import RESIDENT, VISITOR, ProfileStore
from gui import passenger_page
from gui.people_art import label_key
from gui.window import MainWindow, format_clock, format_scale
from i18n import set_language, tr
from i18n import zh_CN, en_US

_APP: QApplication | None = None
#: 模块开始时的样例文件摘要，tearDownModule 里比对
_DATA_FINGERPRINT: str = ""


def setUpModule() -> None:
    global _APP, _DATA_FINGERPRINT
    _APP = QApplication.instance() or QApplication([])
    _DATA_FINGERPRINT = repo_data_fingerprint()


def tearDownModule() -> None:
    # 之前 GUI 用例会直接改写仓库里的 data/profiles.json：商务楼预设一次
    # 生成上千条画像，样例文件被换成 office/1590 条且画像缺 gender。
    # 现在画像库走临时目录，这里再钉一道，回归了立刻能看见。
    if repo_data_fingerprint() != _DATA_FINGERPRINT:
        raise AssertionError(
            "测试改写了 data/profiles.json：GUI 用例必须用 SIMELEVATOR_DATA "
            "指向临时目录，不能写仓库里的样例文件"
        )


#: 测试统一用「小楼」容量，否则商务楼预设会一次生成两千多条画像、
#: 乘以 7 个算法后每个用例都要跑很久。需要真实预设的用例请显式传入。
SMALL_CAPACITY = {"units_per_floor": 1, "occupancy_rate": 0.5, "occupants_per_unit": (2, 2)}


def use_building(page, kind: str, rebuild=None, **capacity) -> None:
    """把大楼切成指定楼型；capacity 可覆盖任意一个容量字段。"""
    fields = {
        "resident_share": BUILDING_PRESETS[kind].resident_share,
        **SMALL_CAPACITY,
        **capacity,
    }
    page.apply_building(Building(kind, **fields), rebuild=rebuild)


def repo_data_fingerprint() -> str:
    """仓库样例画像的摘要，用来发现测试偷偷改写了它。"""
    path = Path(__file__).resolve().parent.parent / "data" / "profiles.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


class I18nTests(unittest.TestCase):
    def test_profile_keys_exist_in_both_languages(self) -> None:
        keys = {k for k in zh_CN.TEXT if k.startswith(("profile.", "nav.", "weekday.", "stats.abandon", "settings.scale", "settings.profile", "settings.open", "settings.start", "settings.time", "building."))}
        self.assertTrue(keys)
        for key in keys:
            self.assertIn(key, en_US.TEXT, msg=f"missing in en_US: {key}")

    def test_language_files_have_identical_keys(self) -> None:
        self.assertEqual(set(zh_CN.TEXT), set(en_US.TEXT))

    def test_switch_language_changes_text(self) -> None:
        set_language("zh_CN")
        self.assertEqual(set_language("zh_CN"), None)
        from i18n import current_language, tr

        self.assertEqual(current_language(), "zh_CN")
        self.assertEqual(tr("nav.passengers"), zh_CN.TEXT["nav.passengers"])
        set_language("en_US")
        self.assertEqual(tr("nav.passengers"), en_US.TEXT["nav.passengers"])
        set_language("zh_CN")

    def test_profile_placeholders_format(self) -> None:
        set_language("en_US")
        from i18n import tr

        self.assertIn("3", tr("profile.leg_count", n=3))
        set_language("zh_CN")

    def test_dead_key_removed(self) -> None:
        """住客已无常去楼层，旧键必须同时从两种语言中移除。"""
        self.assertNotIn("profile.field.main_floor", zh_CN.TEXT)
        self.assertNotIn("profile.field.main_floor", en_US.TEXT)
        self.assertIn("profile.field.dest_floor", zh_CN.TEXT)
        self.assertIn("profile.field.dest_floor", en_US.TEXT)

    def test_both_languages_have_identical_keys(self) -> None:
        self.assertEqual(set(zh_CN.TEXT), set(en_US.TEXT))


class _TempStore:
    """ProfileStore 替身，隔离测试数据。building 透传以免出现两份状态。"""

    def __init__(self, path: Path):
        from core.profiles import ProfileStore

        self._impl = ProfileStore(path)

    @property
    def building(self):
        return self._impl.building

    @building.setter
    def building(self, value) -> None:
        self._impl.building = value

    def load(self):
        return self._impl.load()

    def save(self, profiles=None):
        self._impl.save(profiles)

    def next_index(self) -> int:
        return self._impl.next_index()


class WindowTestCase(unittest.TestCase):
    """在临时目录里跑主窗口，绝不碰仓库里的 data/profiles.json。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name) / "profiles.json"
        # gui.passenger_page.DATA_PATH 是 import 时算好的模块级常量，
        # 事后改 os.environ 已经来不及，所以直接替换这个属性。
        # env_patcher 顺带设上，让不经过 GUI 的路径也落在临时目录，
        # 并且用 addCleanup 恢复，不把污染留给后面的用例。
        env_patcher = mock.patch.dict(
            os.environ, {"SIMELEVATOR_DATA": str(self._tmp_path)}
        )
        env_patcher.start()
        self.addCleanup(env_patcher.stop)
        path_patcher = mock.patch.object(
            passenger_page, "DATA_PATH", self._tmp_path
        )
        path_patcher.start()
        self.addCleanup(path_patcher.stop)
        # 仍然 mock 掉 ProfileStore 构造，双保险：万一将来有代码绕过
        # DATA_PATH 直接 new ProfileStore(...)，也落在临时目录里
        patcher = mock.patch(
            "gui.passenger_page.ProfileStore",
            lambda path: _TempStore(Path(self._tmp.name) / "profiles.json"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # 未 mock 的模态框在 offscreen 下会永远阻塞：直接报错而不是挂起
        guard = mock.patch(
            "gui.passenger_page.QMessageBox.exec",
            side_effect=AssertionError("测试里弹出了未 mock 的模态对话框"),
        )
        guard.start()
        self.addCleanup(guard.stop)
        self.addCleanup(self._tmp.cleanup)
        set_language("zh_CN")
        self.window = MainWindow()
        self.window.resize(1600, 900)
        self.window.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        set_language("zh_CN")


class WindowTests(WindowTestCase):
    def test_two_pages_with_golden_split(self) -> None:
        self.assertEqual(self.window.stack.count(), 2)
        # 直接取引擎持有的 splitter，不按 layout 下标去猜：仿真页顶部
        # 加了图例条之后 itemAt(0) 已经不是 splitter 了
        sizes = self.window.splitter.sizes()
        self.assertAlmostEqual(sizes[0] / sum(sizes), 0.618, delta=0.02)
        self.window.show_page(1)
        _APP.processEvents()
        page_splitter = self.window.passengers.layout().itemAt(0).widget()
        sizes = page_splitter.sizes()
        self.assertAlmostEqual(sizes[0] / sum(sizes), 0.618, delta=0.02)

    def test_navigation_switches_pages(self) -> None:
        self.window.nav_passengers.click()
        _APP.processEvents()
        self.assertEqual(self.window.stack.currentIndex(), 1)
        self.window.nav_simulation.click()
        _APP.processEvents()
        self.assertEqual(self.window.stack.currentIndex(), 0)

    def test_demand_settings_disabled(self) -> None:
        for _label, widget in self.window.panel._demand_fields:
            self.assertFalse(widget.isEnabled())
        self.assertTrue(self.window.panel.passengers_button.isEnabled())

    def test_runner_uses_profiles(self) -> None:
        config = self.window.panel.collect_config()
        self.assertEqual(config.passenger_source, "profile")
        for sim in self.window.runner.sims.values():
            self.assertEqual(type(sim.generator).__name__, "ProfileGenerator")

    def test_stats_include_abandoned(self) -> None:
        self.window.runner.step(120.0)
        results = self.window.runner.results()
        self.assertTrue(results)
        for snap in results.values():
            self.assertIn("abandoned", snap)
            self.assertIn("abandon_rate", snap)

    def test_time_scale_applied(self) -> None:
        self.assertGreaterEqual(self.window.panel.time_scale_value(), 1.0)
        self.assertGreaterEqual(self.window.panel.time_scale.findData(10.0), 0)
        self.assertEqual(self.window.panel.time_scale_value(), 1.0)

    def test_passenger_page_loads_samples(self) -> None:
        page = self.window.passengers
        self.assertEqual(len(page.profiles), 9)
        self.assertGreaterEqual(page.list.count(), 1)

    def test_add_profile_appears_in_list(self) -> None:
        page = self.window.passengers
        before = len(page.profiles)
        page.add(RESIDENT)
        _APP.processEvents()
        self.assertEqual(len(page.profiles), before + 1)
        self.assertIsNotNone(page.current())

    def test_batch_generation(self) -> None:
        page = self.window.passengers
        use_building(page, "residential", rebuild=True, units_per_floor=1, occupancy_rate=0.5)
        planned = page.population.total
        page._do_batch()
        _APP.processEvents()
        self.assertEqual(len(page.profiles), planned + planned)
        self.assertFalse(page.batch_row.isVisible())

    def test_delete_profile(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        before = len(page.profiles)
        page.delete_current()
        _APP.processEvents()
        self.assertEqual(len(page.profiles), before - 1)

    def test_duplicate_profile(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        before = len(page.profiles)
        page.duplicate()
        _APP.processEvents()
        self.assertEqual(len(page.profiles), before + 1)

    def test_edit_fields_persist(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        page.jitter.setValue(11)
        page.companions.setValue(3)
        _APP.processEvents()
        profile = page.current()
        self.assertEqual(profile.jitter_min, 11)
        self.assertEqual(profile.companions, 3)

    def test_leg_add_remove(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        self.assertEqual(page.current().kind, RESIDENT)
        before = page.legs_table.rowCount()
        page._add_leg()
        _APP.processEvents()
        self.assertEqual(page.legs_table.rowCount(), before + 1)
        page.legs_table.setCurrentCell(page.legs_table.rowCount() - 1, 0)
        page._remove_leg()
        _APP.processEvents()
        self.assertEqual(page.legs_table.rowCount(), before)

    def test_kind_switch_visibility(self) -> None:
        page = self.window.passengers
        self.window.show_page(1)
        _APP.processEvents()
        for i in range(page.list.count()):
            page.list.setCurrentRow(i)
            _APP.processEvents()
            if page.current().kind == RESIDENT:
                self.assertTrue(page.home_floor.isVisible())
                self.assertTrue(page.legs_group.isVisible())
                self.assertFalse(page.arrive.isVisible())
                # 住客不再有常去楼层
                self.assertFalse(page.main_floor.isVisible())
                self.assertFalse(page.main_row[0].isVisible())
            else:
                self.assertFalse(page.home_floor.isVisible())
                self.assertTrue(page.arrive.isVisible())
                self.assertFalse(page.legs_group.isVisible())
                # 访客用该字段表示目的层
                self.assertTrue(page.main_floor.isVisible())
                self.assertTrue(page.main_row[0].isVisible())

    def test_new_resident_is_complete_and_persisted(self) -> None:
        from core.profiles import needs_fill

        page = self.window.passengers
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.kind, RESIDENT)
        self.assertTrue(profile.legs, msg="新建住客应立即获得随机作息")
        self.assertIsNone(profile.main_floor)
        self.assertFalse(needs_fill(profile))
        # 日程表应显示生成的作息
        self.assertEqual(page.legs_table.rowCount(), len(profile.legs))
        # 已落盘
        stored = [p for p in page.store.load() if p.pid == profile.pid]
        self.assertEqual(len(stored), 1)
        self.assertEqual(len(stored[0].legs), len(profile.legs))
        self.assertIsNone(stored[0].main_floor)

    def test_new_visitor_is_complete_and_persisted(self) -> None:
        from core.profiles import needs_fill

        page = self.window.passengers
        page.add(VISITOR)
        _APP.processEvents()
        profile = page.current()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.kind, VISITOR)
        self.assertIsNotNone(profile.main_floor)
        self.assertFalse(needs_fill(profile))

    def test_empty_schedule_is_kept(self) -> None:
        page = self.window.passengers
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()
        while page.legs_table.rowCount() > 0:
            page.legs_table.setCurrentCell(0, 0)
            page._remove_leg()
            _APP.processEvents()
        self.assertEqual(page.current().legs, [], msg="删光行程后不应自动补回")
        stored = [p for p in page.store.load() if p.pid == profile.pid]
        self.assertEqual(stored[0].legs, [])

    def test_legless_resident_makes_no_events(self) -> None:
        from core.profile_generator import ProfileGenerator

        page = self.window.passengers
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()
        while page.legs_table.rowCount() > 0:
            page.legs_table.setCurrentCell(0, 0)
            page._remove_leg()
            _APP.processEvents()
        config = self.window.panel.collect_config()
        gen = ProfileGenerator(config, [profile])
        self.assertEqual(gen.pop_until(2 * 86400), [])

    def test_seed_change_does_not_re_roll_saved_profile(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        before = [
            (l.time_min, l.target_floor, l.stay_min) for l in page.current().legs
        ]
        self.window.panel.seed.setValue(1234)
        _APP.processEvents()
        after = [(l.time_min, l.target_floor, l.stay_min) for l in page.current().legs]
        self.assertEqual(before, after, msg="改种子不应重掷已落盘的作息")

    def test_seed_change_applies_to_new_profiles_only(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        frozen = [(l.time_min, l.target_floor, l.stay_min) for l in page.current().legs]
        self.window.panel.seed.setValue(555)
        _APP.processEvents()
        self.assertEqual(
            [(l.time_min, l.target_floor, l.stay_min) for l in page.current().legs],
            frozen,
        )

    def test_floors_decrease_clamps_stored(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        self.window.panel.floors.setValue(20)
        _APP.processEvents()
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()
        page.legs_table.cellWidget(0, 1).setValue(19)
        _APP.processEvents()
        self.assertEqual(page.current().legs[0].target_floor, 19)
        self.window.panel.floors.setValue(6)
        _APP.processEvents()
        for p in page.profiles:
            if p.home_floor is not None:
                self.assertLessEqual(p.home_floor, 6)
            if p.main_floor is not None:
                self.assertLessEqual(p.main_floor, 6)
            for leg in p.legs:
                self.assertLessEqual(leg.target_floor, 6)

    def test_add_leg_default_target(self) -> None:
        page = self.window.passengers
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()
        before = page.legs_table.rowCount()
        page._add_leg()
        _APP.processEvents()
        self.assertEqual(page.legs_table.rowCount(), before + 1)
        new_leg = page.current().legs[-1]
        self.assertNotEqual(new_leg.target_floor, profile.home_floor)

    def test_editing_leg_widget_is_committed(self) -> None:
        """日程表用 cellWidget，其信号不经过 itemChanged，必须自行提交。"""
        page = self.window.passengers
        page.add(RESIDENT)
        _APP.processEvents()
        profile = page.current()

        page.legs_table.cellWidget(0, 1).setValue(3)
        page.legs_table.cellWidget(0, 2).setValue(240)
        from PySide6.QtCore import QTime

        page.legs_table.cellWidget(0, 0).setTime(QTime(6, 30))
        _APP.processEvents()

        leg = page.current().legs[0]
        self.assertEqual(leg.target_floor, 3)
        self.assertEqual(leg.stay_min, 240)
        self.assertEqual(leg.time_min, 6 * 60 + 30)
        stored = [p for p in page.store.load() if p.pid == profile.pid][0]
        self.assertEqual(stored.legs[0].target_floor, 3)
        self.assertEqual(stored.legs[0].stay_min, 240)
        self.assertEqual(stored.legs[0].time_min, 6 * 60 + 30)

    def test_visitor_conversion(self) -> None:
        page = self.window.passengers
        page.list.setCurrentRow(0)
        _APP.processEvents()
        page.kind_combo.setCurrentIndex(page.kind_combo.findData(VISITOR))
        _APP.processEvents()
        profile = page.current()
        self.assertEqual(profile.kind, VISITOR)
        self.assertIsNone(profile.home_floor)
        self.assertEqual(profile.legs, [])
        self.assertIsNotNone(profile.visitor_arrive)

    def test_preview_shows_round_trip(self) -> None:
        page = self.window.passengers
        for i in range(page.list.count()):
            page.list.setCurrentRow(i)
            _APP.processEvents()
            text = page.preview_label.text()
            self.assertIn("→", text)

    def test_search_filters_list(self) -> None:
        page = self.window.passengers
        page.search.setText("P001")
        _APP.processEvents()
        self.assertEqual(page.list.count(), 1)
        page.search.setText("zzz-no-match")
        _APP.processEvents()
        self.assertEqual(page.list.count(), 0)
        page.search.clear()
        _APP.processEvents()
        self.assertEqual(page.list.count(), 9)

    def test_kind_filter(self) -> None:
        page = self.window.passengers
        page.filter_combo.setCurrentIndex(page.filter_combo.findData(VISITOR))
        _APP.processEvents()
        for i in range(page.list.count()):
            self.assertEqual(page.current().kind, VISITOR)
        page.filter_combo.setCurrentIndex(0)
        _APP.processEvents()

    def test_retranslate_updates_page(self) -> None:
        set_language("en_US")
        _APP.processEvents()
        self.assertEqual(self.window.nav_simulation.text(), en_US.TEXT["nav.simulation"])
        self.assertEqual(self.window.nav_passengers.text(), en_US.TEXT["nav.passengers"])
        self.assertIn("Home floor", self.window.passengers.home_row[0].text())
        set_language("zh_CN")
        _APP.processEvents()
        self.assertEqual(self.window.nav_passengers.text(), zh_CN.TEXT["nav.passengers"])

    def test_profiles_change_reconfigures_runner(self) -> None:
        page = self.window.passengers
        before = len(page.profiles)
        page.add(RESIDENT)
        _APP.processEvents()
        self.assertEqual(len(self.window.runner.profiles), before + 1)

    def test_floors_change_updates_page(self) -> None:
        self.window.panel.floors.setValue(20)
        _APP.processEvents()
        self.assertEqual(self.window.passengers.floors, 20)
        self.assertEqual(self.window.passengers.home_floor.maximum(), 20)


class BuildingUITests(WindowTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.page = self.window.passengers
        # 楼层数直接进容量公式，先压低再用小容量楼，保持每个用例都很快
        self.window.panel.floors.setValue(10)
        use_building(
            self.page,
            RESIDENTIAL,
            rebuild=True,
            units_per_floor=3,
            occupancy_rate=1.0,
            occupants_per_unit=(2, 2),
        )

    def test_building_combo_has_both_types(self) -> None:
        kinds = [
            self.page.building_combo.itemData(i)
            for i in range(self.page.building_combo.count())
        ]
        self.assertEqual(kinds, ["residential", "office"])

    def test_share_spin_reflects_building(self) -> None:
        self.assertEqual(self.page.share_spin.value(), 90)

    def test_capacity_widgets_reflect_building(self) -> None:
        self.assertEqual(self.page.occupancy_spin.value(), 100)
        self.assertEqual(self.page.units_spin.value(), 3)
        self.assertEqual(self.page.occupants_min_spin.value(), 2)
        self.assertEqual(self.page.occupants_max_spin.value(), 2)

    def test_switching_type_offers_rebuild(self) -> None:
        asked = []

        def fake_confirm():
            asked.append(len(self.page.profiles))
            return None  # 取消

        self.page._confirm_rebuild = fake_confirm
        self.page.building_combo.setCurrentIndex(
            self.page.building_combo.findData("office")
        )
        _APP.processEvents()
        self.assertEqual(asked, [len(self.page.profiles)])
        self.assertEqual(self.page.building.kind, "residential")

    def test_cancel_keeps_profiles(self) -> None:
        before = [p.to_json() for p in self.page.profiles]
        self.page._confirm_rebuild = lambda: None
        use_building(self.page, OFFICE)
        self.assertEqual([p.to_json() for p in self.page.profiles], before)
        self.assertEqual(self.page.building.kind, "residential")

    def test_rebuild_replaces_profiles(self) -> None:
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE, units_per_floor=1, occupants_per_unit=(2, 2))
        self.assertEqual(self.page.building.kind, "office")
        self.assertAlmostEqual(self.page.building.resident_share, 0.2)
        self.assertEqual(len(self.page.profiles), self.page.population.total)
        residents = [p for p in self.page.profiles if p.kind == RESIDENT]
        self.assertTrue(residents)
        for p in residents:
            self.assertEqual(p.home_floor, 1)
            self.assertGreaterEqual(p.legs[0].target_floor, 2)

    def test_new_only_keeps_profiles(self) -> None:
        before = [p.to_json() for p in self.page.profiles]
        self.page._confirm_rebuild = lambda: False
        use_building(self.page, OFFICE)
        self.assertEqual([p.to_json() for p in self.page.profiles], before)
        self.assertEqual(self.page.building.kind, "office")
        self.page.add(RESIDENT)
        added = self.page.profiles[-1]
        self.assertEqual(added.home_floor, 1)

    def test_share_change_does_not_rebuild(self) -> None:
        before = [p.to_json() for p in self.page.profiles]
        self.page.share_spin.setValue(50)
        _APP.processEvents()
        self.assertEqual([p.to_json() for p in self.page.profiles], before)
        self.assertAlmostEqual(self.page.building.resident_share, 0.5)

    def test_switching_type_resets_capacity_to_preset(self) -> None:
        self.page._confirm_rebuild = lambda: False
        self.page.occupancy_spin.setValue(20)
        self.page.units_spin.setValue(7)
        self.page.occupants_max_spin.setValue(30)
        _APP.processEvents()
        self.page.building_combo.setCurrentIndex(
            self.page.building_combo.findData(OFFICE)
        )
        _APP.processEvents()
        preset = BUILDING_PRESETS[OFFICE]
        self.assertEqual(self.page.building.kind, OFFICE)
        self.assertEqual(self.page.building.occupancy_rate, preset.occupancy_rate)
        self.assertEqual(self.page.building.units_per_floor, preset.units_per_floor)
        self.assertEqual(
            self.page.building.occupants_per_unit, preset.occupants_per_unit
        )
        self.assertEqual(self.page.occupancy_spin.value(), 70)
        self.assertEqual(self.page.units_spin.value(), preset.units_per_floor)
        self.assertEqual(self.page.occupants_min_spin.value(), 8)
        self.assertEqual(self.page.occupants_max_spin.value(), 30)

    def test_population_preview_matches_building(self) -> None:
        pop = self.page.population
        self.assertIn(str(pop.residents), self.page.population_label.text())
        self.assertIn(str(pop.visitors), self.page.population_label.text())
        self.assertIn(str(pop.total), self.page.population_label.text())

    def test_capacity_change_refreshes_preview(self) -> None:
        before = self.page.population.total
        self.page.units_spin.setValue(6)
        _APP.processEvents()
        after = self.page.population.total
        self.assertEqual(self.page.building.units_per_floor, 6)
        self.assertEqual(after, 2 * before)
        self.assertIn(str(after), self.page.population_label.text())

    def test_occupancy_change_refreshes_preview(self) -> None:
        self.page.occupancy_spin.setValue(100)
        _APP.processEvents()
        self.assertEqual(self.page.building.occupancy_rate, 1.0)
        self.assertIn(
            str(self.page.population.total), self.page.population_label.text()
        )

    def test_occupant_range_change_refreshes_preview(self) -> None:
        before = self.page.population.total
        self.page.occupants_max_spin.setValue(6)
        self.page.occupants_min_spin.setValue(4)
        _APP.processEvents()
        self.assertEqual(self.page.building.occupants_per_unit, (4, 6))
        self.assertGreater(self.page.population.total, before)
        self.assertIn(
            str(self.page.population.total), self.page.population_label.text()
        )

    def test_occupant_range_is_always_ordered(self) -> None:
        """下限高于上限时自动排序，并把控件同步回正确顺序。"""
        self.page.occupants_min_spin.setValue(9)
        _APP.processEvents()
        self.assertEqual(self.page.building.occupants_per_unit, (2, 9))
        self.assertEqual(self.page.occupants_min_spin.value(), 2)
        self.assertEqual(self.page.occupants_max_spin.value(), 9)
        self.page.occupants_max_spin.setValue(5)
        _APP.processEvents()
        self.assertEqual(self.page.building.occupants_per_unit, (2, 5))

    def test_floors_change_recomputes_population(self) -> None:
        before = self.page.population.total
        self.window.panel.floors.setValue(self.window.panel.floors.value() + 6)
        _APP.processEvents()
        self.assertGreater(self.page.population.total, before)
        self.assertIn(
            str(self.page.population.total), self.page.population_label.text()
        )

    def test_large_population_shows_warning(self) -> None:
        self.assertFalse(self.page.population_hint.isVisible())
        use_building(
            self.page,
            OFFICE,
            rebuild=False,
            units_per_floor=4,
            occupancy_rate=100,
            occupants_per_unit=(30, 30),
        )
        _APP.processEvents()
        self.assertGreater(self.page.population.total, 500)
        self.assertTrue(self.page.population_hint.isVisibleTo(self.page))
        self.assertEqual(
            self.page.population_hint.text(), tr("building.population.warn")
        )

    def test_batch_total_is_read_only(self) -> None:
        self.assertFalse(hasattr(self.page, "batch_count"))
        self.assertEqual(
            self.page.batch_total.text(),
            tr("profile.batch.total", n=self.page.population.total),
        )

    def test_batch_adds_previewed_count(self) -> None:
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE, units_per_floor=1, occupants_per_unit=(2, 2))
        planned = self.page.population.total
        before = len(self.page.profiles)
        self.page.batch_confirm.click()
        _APP.processEvents()
        self.assertEqual(len(self.page.profiles), before + planned)

    def test_batch_uses_building_ratio(self) -> None:
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE, units_per_floor=1, occupants_per_unit=(2, 2))
        planned = self.page.population.total
        self.page.batch_confirm.click()
        _APP.processEvents()
        fresh = self.page.profiles[-planned:]
        share = sum(1 for p in fresh if p.kind == RESIDENT) / len(fresh)
        self.assertAlmostEqual(share, 0.2, delta=0.01)

    def test_batch_row_has_no_kind_selector(self) -> None:
        self.assertFalse(hasattr(self.page, "batch_kind"))

    def test_office_labels_call_residents_staff(self) -> None:
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE)
        self.assertEqual(
            self.page.add_resident_btn.text(), tr("profile.add_staff")
        )
        index = self.page.filter_combo.findData(RESIDENT)
        self.assertEqual(self.page.filter_combo.itemText(index), tr("profile.kind.staff"))
        use_building(self.page, RESIDENTIAL, rebuild=True)
        self.assertEqual(
            self.page.add_resident_btn.text(), tr("profile.add_resident")
        )
        self.assertEqual(
            self.page.filter_combo.itemText(index), tr("profile.filter.resident")
        )

    def test_building_badge_follows_switch(self) -> None:
        self.assertIn("90", self.window.building_badge.text())
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE)
        _APP.processEvents()
        self.assertIn("20", self.window.building_badge.text())
        self.assertIn(tr("building.office"), self.window.building_badge.text())

    def test_badge_shows_total_passengers(self) -> None:
        self.assertIn(
            tr("building.total", n=self.page.population.total),
            self.window.building_badge.text(),
        )
        self.page.units_spin.setValue(4)
        _APP.processEvents()
        self.assertIn(
            tr("building.total", n=self.page.population.total),
            self.window.building_badge.text(),
        )

    def test_building_persists_through_store(self) -> None:
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE, units_per_floor=3, occupants_per_unit=(9, 11))
        self.assertEqual(self.page.store.building.kind, "office")
        self.assertEqual(self.page.store._impl.building.kind, "office")
        self.assertEqual(self.page.store._impl.building.units_per_floor, 3)
        self.assertEqual(self.page.store._impl.building.occupants_per_unit, (9, 11))

    def test_default_target_is_building_aware(self) -> None:
        self.assertEqual(self.page._default_target(12), 1)
        self.page._confirm_rebuild = lambda: True
        use_building(self.page, OFFICE)
        self.assertEqual(self.page._default_target(1), 2)


class PeopleMixUITests(WindowTestCase):
    """人群构成：四个占比输入、三个特殊参数、分类人数预览。"""

    def setUp(self) -> None:
        super().setUp()
        self.page = self.window.passengers
        self.window.panel.floors.setValue(10)
        use_building(
            self.page,
            RESIDENTIAL,
            rebuild=True,
            units_per_floor=3,
            occupancy_rate=1.0,
            occupants_per_unit=(2, 2),
        )

    def test_four_mix_spins_exist(self) -> None:
        self.assertEqual(list(self.page.mix_spins), list(PEOPLE_KINDS))
        for spin in self.page.mix_spins.values():
            self.assertEqual(spin.maximum(), 100)

    def test_mix_spins_reflect_building(self) -> None:
        for kind, spin in self.page.mix_spins.items():
            self.assertAlmostEqual(
                spin.value() / 100.0,
                self.page.building.mix_for(kind),
                delta=0.005,
                msg=kind,
            )

    def test_mix_spin_updates_building(self) -> None:
        self.page.mix_spins[MALE].setValue(80)
        _APP.processEvents()
        mix = self.page.building.people_mix
        self.assertGreater(mix[MALE], mix[FEMALE])

    def test_mix_is_normalized_not_summed(self) -> None:
        # 四个占比独立输入，拖大一个不应让总人数或归一化结果爆掉
        self.page.mix_spins[MALE].setValue(400 // 4)
        _APP.processEvents()
        self.assertAlmostEqual(sum(self.page.building.people_mix.values()), 1.0, places=2)

    def test_mix_change_does_not_rebuild_profiles(self) -> None:
        before = [p.to_json() for p in self.page.profiles]
        self.page.mix_spins[WHEELCHAIR].setValue(20)
        _APP.processEvents()
        self.assertEqual([p.to_json() for p in self.page.profiles], before)

    def test_mix_population_preview_matches_counts(self) -> None:
        text = self.page.mix_population_label.text()
        counts = self.page.building.category_counts(self.page.population.total)
        for kind, n in counts.items():
            self.assertIn(str(n), text, msg=f"{kind}={n}")

    def test_special_params_reflect_building(self) -> None:
        preset = BUILDING_PRESETS[RESIDENTIAL]
        self.assertEqual(
            self.page.wheelchair_patience.value(), preset.wheelchair_patience
        )
        self.assertEqual(
            self.page.child_companions_spin.value(), preset.child_min_companions
        )
        self.assertEqual(self.page.child_patience.value(), preset.child_patience)

    def test_special_params_write_into_building(self) -> None:
        self.page.wheelchair_patience.setValue(3.0)
        self.page.child_companions_spin.setValue(4)
        self.page.child_patience.setValue(0.25)
        _APP.processEvents()
        self.assertEqual(self.page.building.wheelchair_patience, 3.0)
        self.assertEqual(self.page.building.child_min_companions, 4)
        self.assertEqual(self.page.building.child_patience, 0.25)

    def test_special_params_persist_through_store(self) -> None:
        self.page.wheelchair_patience.setValue(2.75)
        _APP.processEvents()
        self.assertEqual(self.page.store.building.wheelchair_patience, 2.75)

    def test_mix_persists_through_store(self) -> None:
        self.page.mix_spins[CHILD].setValue(10)
        _APP.processEvents()
        saved = self.page.store.building.people_mix
        self.assertGreater(saved[CHILD], 0)

    def test_mix_survives_retranslate(self) -> None:
        # 占比标签带色块富文本，切换语言后必须仍是「色块 + 名称」
        set_language("en_US")
        _APP.processEvents()
        for kind, label in self.page.mix_labels.items():
            self.assertIn(tr(label_key(kind)), label.text(), msg=kind)
        set_language("zh_CN")

    def test_section_titles_are_translated(self) -> None:
        self.assertEqual(
            self.page.capacity_title.text(), tr("building.capacity_title")
        )
        self.assertEqual(self.page.mix_title.text(), tr("building.mix_title"))


class ProfileGenderUITests(WindowTestCase):
    """画像编辑器里的人群分类下拉框与大号图形预览。"""

    def setUp(self) -> None:
        super().setUp()
        self.page = self.window.passengers
        self.window.panel.floors.setValue(10)
        use_building(
            self.page,
            RESIDENTIAL,
            rebuild=True,
            units_per_floor=3,
            occupancy_rate=1.0,
            occupants_per_unit=(2, 2),
        )
        self.page._confirm_rebuild = lambda: True

    def test_gender_combo_has_four_categories(self) -> None:
        data = [
            self.page.gender_combo.itemData(i)
            for i in range(self.page.gender_combo.count())
        ]
        self.assertEqual(data, list(PEOPLE_KINDS))

    def test_gender_combo_is_disabled_without_selection(self) -> None:
        self.page.list.setCurrentRow(-1)
        _APP.processEvents()
        self.assertIsNone(self.page.current())
        self.assertFalse(self.page.gender_combo.isEnabled())
        self.assertFalse(self.page.person_preview.isEnabled())

    def test_every_row_shows_its_own_gender(self) -> None:
        for row in range(self.page.list.count()):
            self.page.list.setCurrentRow(row)
            _APP.processEvents()
            profile = self.page.current()
            self.assertIsNotNone(profile)
            self.assertEqual(
                self.page.gender_combo.currentData(),
                profile.gender,
                msg=f"row={row}",
            )
            self.assertEqual(self.page.person_preview._gender, profile.gender)

    def test_changing_gender_persists(self) -> None:
        self.page.list.setCurrentRow(0)
        _APP.processEvents()
        self.page.gender_combo.setCurrentIndex(
            self.page.gender_combo.findData(CHILD)
        )
        _APP.processEvents()
        self.assertEqual(self.page.current().gender, CHILD)
        # 落盘校验：直接读临时画像库，不依赖 store 的内部结构
        raw = json.loads(self._tmp_path.read_text(encoding="utf-8"))
        self.assertIn(CHILD, {p["gender"] for p in raw["profiles"]})

    def test_person_preview_follows_gender(self) -> None:
        self.page.list.setCurrentRow(0)
        _APP.processEvents()
        for kind in PEOPLE_KINDS:
            self.page.gender_combo.setCurrentIndex(
                self.page.gender_combo.findData(kind)
            )
            _APP.processEvents()
            self.assertEqual(self.page.person_preview._gender, kind, msg=kind)

    def test_person_preview_falls_back_for_bad_value(self) -> None:
        self.page.person_preview.set_gender("unicorn")
        self.assertEqual(self.page.person_preview._gender, MALE)

    def test_profile_kind_still_editable(self) -> None:
        # 加了人群下拉框不能挤掉住客/访客选择
        self.page.list.setCurrentRow(0)
        _APP.processEvents()
        self.assertTrue(self.page.kind_combo.isEnabled())


class LegendTests(WindowTestCase):
    """仿真页顶部的图例条。"""

    def test_legend_lists_every_category(self) -> None:
        self.assertEqual(list(self.window.legend_labels), list(PEOPLE_KINDS))
        for kind, label in self.window.legend_labels.items():
            self.assertEqual(label.text(), tr(label_key(kind)), msg=kind)

    def test_legend_explains_arrows(self) -> None:
        texts = [label.text() for label in self.window.legend_arrow_labels]
        self.assertEqual(texts, [tr("view.up"), tr("view.down")])

    def test_legend_has_hint(self) -> None:
        self.assertEqual(self.window.legend_hint.text(), tr("people.legend.hint"))

    def test_legend_follows_language(self) -> None:
        set_language("en_US")
        _APP.processEvents()
        for kind, label in self.window.legend_labels.items():
            self.assertEqual(label.text(), tr(label_key(kind)), msg=kind)
        self.assertEqual(
            [label.text() for label in self.window.legend_arrow_labels],
            [tr("view.up"), tr("view.down")],
        )
        set_language("zh_CN")

    def test_legend_sits_above_the_view(self) -> None:
        layout = self.window.sim_page.layout()
        self.assertIs(layout.itemAt(0).widget(), self.window.legend)
        self.assertIs(layout.itemAt(1).widget(), self.window.splitter)


class DataIsolationTests(unittest.TestCase):
    """画像库路径必须可被环境变量改写，测试才不会写脏仓库样例。"""

    def test_data_path_honours_env_var(self) -> None:
        import importlib

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "elsewhere.json"
            with mock.patch.dict(os.environ, {"SIMELEVATOR_DATA": str(target)}):
                reloaded = importlib.reload(passenger_page)
                try:
                    self.assertEqual(reloaded.DATA_PATH, target)
                finally:
                    # 还原成仓库默认路径，别影响后面用例
                    with mock.patch.dict(os.environ, {}, clear=False):
                        os.environ.pop("SIMELEVATOR_DATA", None)
                    importlib.reload(passenger_page)

    def test_data_path_defaults_to_repo_sample(self) -> None:
        expected = (
            Path(__file__).resolve().parent.parent / "data" / "profiles.json"
        )
        self.assertEqual(passenger_page.DATA_PATH, expected)


class ClockAndSpeedTests(WindowTestCase):
    def test_time_scale_options(self) -> None:
        from gui.settings_panel import TIME_SCALE_ITEMS

        self.assertEqual([f for _, f in TIME_SCALE_ITEMS], [1.0, 2.0, 5.0, 10.0])
        self.assertEqual(self.window.panel.time_scale.currentData(), 1.0)

    def test_clock_label_shows_day_and_time(self) -> None:
        text = self.window.clock_label.text()
        self.assertTrue(text.startswith(tr("sim.clock_day", n=1)))
        self.assertRegex(text, r"\d{2}:\d{2}:\d{2}$")

    def test_clock_advances_with_simulation(self) -> None:
        self.window.runner.step(3600.0)
        self.window._update_clock(1 / 60, 1 / 60)
        self.assertIn(tr("sim.clock_day", n=1), self.window.clock_label.text())
        self.assertNotIn("00:00:00", self.window.clock_label.text())

    def test_clock_rolls_over_to_second_day(self) -> None:
        self.window.runner.step(20 * 3600.0)
        self.window._update_clock(1 / 60, 1 / 60)
        self.assertIn(tr("sim.clock_day", n=2), self.window.clock_label.text())

    def test_paused_clears_speed_chip(self) -> None:
        self.window._update_clock(1 / 60, 0.0166)
        self.assertEqual(self.window.speed_chip.text(), "")

    def test_smooth_chip_shows_effective_scale(self) -> None:
        self.window._running = True
        self.window._update_clock(0.1, 0.1)
        self.assertIn(tr("sim.mode.smooth"), self.window.speed_chip.text())
        self.assertIn("×1.0", self.window.speed_chip.text())

    def test_fast_chip_shows_effective_scale(self) -> None:
        self.window._running = True
        self.window._update_clock(1 / 60, 2.0)
        self.assertIn(tr("sim.mode.fast"), self.window.speed_chip.text())
        self.assertIn("×120", self.window.speed_chip.text())

    def test_chip_colors_differ_by_mode(self) -> None:
        self.window._running = True
        self.window._update_clock(1 / 60, 1 / 60)
        smooth = self.window.speed_chip.styleSheet()
        self.window._update_clock(1 / 60, 2.0)
        self.assertNotEqual(smooth, self.window.speed_chip.styleSheet())
        self.assertIn("#2b5fb8", smooth)

    def test_chip_tooltip_reports_effective_scale(self) -> None:
        self.window._running = True
        self.window._update_clock(1 / 60, 2.0)
        self.assertEqual(
            self.window.speed_chip.toolTip(), tr("sim.clock_tip", v="120")
        )

    def test_scale_formatting(self) -> None:
        self.assertEqual(format_scale(1.0), "1.0")
        self.assertEqual(format_scale(2.5), "2.5")
        self.assertEqual(format_scale(9.96), "10.0")
        self.assertEqual(format_scale(119.7), "120")

    def test_clock_formatting(self) -> None:
        self.assertEqual(
            format_clock(0.0, 7 * 60), f"{tr('sim.clock_day', n=1)} 07:00:00"
        )
        self.assertEqual(
            format_clock(3661.0, 23 * 60 + 30), f"{tr('sim.clock_day', n=2)} 00:31:01"
        )


if __name__ == "__main__":
    unittest.main()
