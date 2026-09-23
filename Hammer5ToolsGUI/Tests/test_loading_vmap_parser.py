from core.bridge import CoreBridge, ValveMapDocument, ValveMapEntity, ValveMapNode
from gui.editors.loading_editor.vmap_parser import parse


def test_parse_returns_point_camera_presentation_data(monkeypatch):
    document = ValveMapDocument(
        "maps/example.vmap",
        ValveMapNode("world", "CMapWorld", {}, ()),
        (
            ValveMapNode("", "CMapSavedCamera", {
                "origin": "4 5 6", "angles": "7 8 9", "fov": "75", "cameraName": "",
            }, ()),
        ),
        (
            ValveMapEntity(
                "point_camera",
                "1 2 3",
                "10 20 30",
                {
                    "classname": "point_camera",
                    "targetname": "camera",
                    "FOV": "90",
                },
            ),
            ValveMapEntity("light_environment", None, None, {}),
        ),
        (),
        None,
        None,
    )

    class FakeBridge:
        def read_valve_map(self, path):
            assert path == "maps/example.vmap"
            return document

    monkeypatch.setattr(CoreBridge, "instance", classmethod(lambda cls: FakeBridge()))

    cameras = parse("maps/example.vmap", show_entity_properties=True)

    assert parse("maps/example.vmap", saved_cameras=True) == [{
        "classname": "CMapSavedCamera",
        "origin": "4 5 6",
        "angles": "7 8 9",
        "targetname": None,
        "FOV": "75",
    }]

    assert cameras == [{
        "classname": "point_camera",
        "origin": "1 2 3",
        "angles": "10 20 30",
        "targetname": "camera",
        "FOV": "90",
        "entity_properties": {
            "classname": "point_camera",
            "targetname": "camera",
            "FOV": "90",
        },
    }]
