soundevent_editor_properties = [
    # Float
    {'Volume': {'volume': 1}},
    {'Delay': {'delay': 1}},
    {'Pitch': {'pitch': 1}},
    {'Volume Random Min': {'volume_random_min': -0.5}},
    {'Volume Random Max': {'volume_random_max': 0.5}},
    {'Pitch Random Min': {'pitch_random_min': -0.5}},
    {'Pitch Random Max': {'pitch_random_max': -0.5}},
    {'Randomize Position Min Radius': {'randomize_position_min_radius': 2000}},
    {'Randomize Position Max Radius': {'randomize_position_max_radius': 3000}},
    {'Retrigger Interval Min': {'retrigger_interval_min': 10}},
    {'Retrigger Interval Max': {'retrigger_interval_max': 30}},
    {'Occlusion Intensity': {'occlusion_intensity': 0.0}},
    {'Distance Effect Mix': {'distance_effect_mix': 0.0}},
    {'Reverb Wet': {'reverb_wet': 1.0}},
    {'Occlusion Frequency Scale': {'occlusion_frequency_scale ': 1.0}},
    {'Vsnd Duration': {'vsnd_duration': 10}},


    # Files
    {'Sound Files track': {'vsnd_files_track_01': []}},

    # Vector3
    {'Position': {'position': [0, 0, 0]}},

    # Bool
    {'Enable Child Events': {'enable_child_events': True}},
    {'Enable Retrigger': {'enable_retrigger': True}},
    {'Restrict Source Reverb': {'restrict_source_reverb': True}},
    {'Randomize Position Hemisphere': {'randomize_position_hemisphere': False}},
    {'Use Distance Unfiltered Stereo Mapping Curve': {'use_distance_unfiltered_stereo_mapping_curve': True}},
    {'Use Distance Volume Mapping Curve': {'use_distance_volume_mapping_curve': True}},
    {'Use Time Volume Mapping Curve': {'use_time_volume_mapping_curve': True}},
    {'Override Dsp Preset': {'override_dsp_preset': True}},
    {'Set Child Position': {'set_child_position': True}},
    {'Position Relative To Player': {'position_relative_to_player': False}},
    {'Use World Position': {'use_world_position': False}},

    # Combobox
    {'Dsp Preset': {'dsp_preset': 'reverb_9_mediumChamber'}},
    {'Soundevent 01': {'soundevent_01': ''}},
    {'Mixgroup': {'mixgroup': 'Amb_Common'}},
    {'Type': {'type': 'csgo_mega'}},
    {'Base': {'base': 'amb.base'}},

    # Curve
    {'Distance Volume Mapping Curve': {'distance_volume_mapping_curve': [[97.14286, 1.0, -0.001763, -0.001763, 2.0, 3.0], [2000.0, 0.0, -0.000526, -0.000526, 1.0, 1.0]]}},
    {'Fadetime Volume Mapping Curve': {'fadetime_volume_mapping_curve': [[0.0, 1.0, -1.223776, -1.223776, 2.0, 3.0], [0.691429, 0.0, 0.0, 0.0, 2.0, 3.0]]}},
    {'Distance Unfiltered Stereo Mapping Curve': {'distance_unfiltered_stereo_mapping_curve': [[0.0, 0.0, 0.0, 0.0, 2.0, 3.0], [300.0, 0.0, 0.0, 0.0, 2.0, 3.0]]}},
    {'Time Volume Mapping Curve': {'time_volume_mapping_curve': [[0.0, 0.0, 0.0, 0.0, 2.0, 3.0], [1.0, 1.0, 0.0, 0.0, 2.0, 3.0]]}},
]
dsp_preset_objects = [
    'reverb_2_crawlSpace',
    'reverb_3_smallTunnels',
    'reverb_4_smallCarpetRoom',
    'reverb_5_smallRoom',
    'reverb_6_largeRoom',
    'reverb_7_mediumHall',
    'reverb_8_mediumCarpetRoom',
    'reverb_9_mediumChamber',
    'reverb_10_warehouse',
    'reverb_11_smallBright9',
    'reverb_12_mediumBright',
    'reverb_13_largeBright',
    'reverb_14_brightHallway',
    'reverb_15_largeCarpetRoom',
    'reverb_16_carpetCorridor',
    'reverb_17_smallConcrete',
    'reverb_18_mediumConcrete',
    'reverb_19_largeConcrete',
    'reverb_20_outsideAlley',
    'reverb_21_outsideStreet',
    'reverb_22_outsideOpen',
    'reverb_23_smallBathroom',
    'reverb_24_largeBathroom'
]
type_objects = ['csgo_mega']
mixgroup_objects = ['ArmsRace', 'Weapons', 'UI', 'voip', 'World', 'Music', 'BuyMusic', 'DuckingMusic', 'SelectedMusic', 'All', 'Footsteps', 'Foley', 'Physics', 'BulletImpacts', 'Explosions', 'ExplosionsDistant', 'Ambient', 'WeaponsDistant', 'Exceptions', 'Amb_Common', 'Aztec', 'Assault', 'Baggage', 'Bank', 'Boathouse', 'Canals', 'Cbble', 'Chateau', 'Compound', 'Coop', 'Dust', 'Dust2', 'Havana', 'House', 'Inferno', 'Italy', 'Lunacy', 'Militia', 'Mill', 'Mirage', 'Monastery', 'Nuke', 'Office', 'Overpass', 'Piranesi', 'Port', 'Prodigy', 'Shacks', 'Shoots', 'Train', 'Training', 'Vertigo', 'PlayerDamage', 'KillCard', 'PlayerVictim', 'Anubis', 'VO']
soundevent_blank = {}