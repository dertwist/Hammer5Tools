soundevent_editor_properties = [
    {'volume': '1'},
    {'vsnd_files_track_01': ''},
    {'randomize_position_min_radius': '2000'},
    {'randomize_position_max_radius': '3000'},
    {'retrigger_interval_min': '10'},
    {'retrigger_interval_max': '30'},
    {'base': ''},
    {'pitch': '1'}


]
for item in soundevent_editor_properties:
    for key, value in item.items():
        print(key, value)