"""Loading-screen VMAP presentation adapter."""

from core.bridge import CoreBridge


def parse(dmx_file_path, show_entity_properties=True):
    """Return point-camera presentation data from the shared Core VMAP reader."""
    document = CoreBridge.instance().read_valve_map(dmx_file_path)
    cameras = []
    for entity in document.entities:
        if entity.class_name != "point_camera":
            continue
        camera = {
            "classname": entity.class_name,
            "origin": entity.origin,
            "angles": entity.angles,
            "targetname": entity.properties.get("targetname"),
        }
        for name in (
            "model",
            "rendercolor",
            "renderamt",
            "spawnflags",
            "hammerid",
            "id",
            "FOV",
        ):
            if name in entity.properties:
                camera[name] = entity.properties[name]
        if show_entity_properties:
            camera["entity_properties"] = dict(entity.properties)
        cameras.append(camera)
    return cameras
