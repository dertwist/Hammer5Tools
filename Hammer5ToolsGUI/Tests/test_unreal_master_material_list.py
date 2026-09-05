import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.forms.unreal_porter.master_material_list import (
    MasterMaterialList,
    material_group_is_selected,
    material_group_matches,
)


app = QApplication.instance() or QApplication([])


def _group(index: int, count: int = 2) -> dict:
    stem = f"MI_Material_{index}"
    return {
        "count": count,
        "shader": "csgo_environment.vfx",
        "instances": [(stem, f"Game/Materials/{stem}", {})],
        "textures": {"BaseColor": f"/Game/Textures/T_Material_{index}"},
    }


def test_material_group_filters_match_instances_textures_and_selection():
    info = _group(12)

    assert material_group_matches(info, "M_Master", "master material_12")
    assert material_group_matches(info, "M_Master", "textures/t_material_12")
    assert not material_group_matches(info, "M_Master", "missing")
    assert material_group_is_selected(info, "M_Master", {"mi_material_12"})
    assert material_group_is_selected(info, "M_Master", {"m_master"})
    assert not material_group_is_selected(info, "M_Master", {"mi_material_4"})


def test_material_list_only_creates_widgets_near_the_viewport():
    widget = MasterMaterialList()
    widget.resize(700, 320)
    widget.show()
    groups = {f"M_Master_{index}": _group(index) for index in range(250)}

    widget.populate(groups)
    app.processEvents()

    assert len(widget.shader_selections()) == 250
    assert 0 < len(widget.cards) < 30

    first_card = widget.cards["M_Master_0"]
    first_card.checkbox.setChecked(False)
    first_card.shader_combo.setCurrentIndex(1)
    chosen_shader = first_card.shader_combo.currentText()
    widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())
    app.processEvents()
    assert "M_Master_0" not in widget.cards
    assert widget.enabled_states()["M_Master_0"] is False
    assert widget.shader_selections()["M_Master_0"] == chosen_shader

    widget.set_filters(search_text="M_Master_149")
    app.processEvents()
    assert set(widget.cards) == {"M_Master_149"}

    widget.set_filters(selected_only=True, selected_assets=["Materials/MI_Material_27.uasset"])
    app.processEvents()
    assert set(widget.cards) == {"M_Master_27"}
    widget.close()
