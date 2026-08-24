from src.bridge import CoreBridge, ValveMapDocument, ValveMapEntity
from src.editors.loading_editor.commands.vmap_parser import parse


def test_parse_returns_point_camera_presentation_data(monkeypatch):
    document = ValveMapDocument(
        "maps/example.vmap",
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
