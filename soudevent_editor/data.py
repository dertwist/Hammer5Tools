# data = {'ambient_example.outdoors': {'base': 'amb.soundscapeParent.base', 'enable_child_events': 'True', 'soundevent_01': 'ambient_example.outdoors.wind'}, 'ambient_example.outdoors.wind': {'base': 'amb.looping.stereo.base', 'volume': '0.7', 'pitch': '0.8', 'vsnd_files_track_01': 'sounds/ambient/dust2/wind_sand_01.vsnd'}, 'ambient_example.outdoors.airplanes': {'base': 'amb.intermittent.randomAroundPlayer.base', 'volume': '0.7', 'randomize_position_min_radius': '2000.0', 'randomize_position_max_radius': '3000.0', 'retrigger_interval_min': '11.0', 'retrigger_interval_max': '30.0', 'vsnd_files_track_01': 'sounds/ambient/dust2/airplane_03.vsnd'}}
data = {'ambient_example.indoors.rockfalls': {'base': 'amb.intermittent.randomAroundPlayer.base', 'volume': 0.7, 'randomize_position_min_radius': 500.0, 'randomize_position_max_radius': 1000.0, 'randomize_position_hemisphere': False, 'retrigger_interval_min': 5.0, 'retrigger_interval_max': 15.0, 'retrigger_radius': 1000.0, 'vsnd_files_track_01': ['sounds/ambient/dust2/rockfall_01.vsnd', 'sounds/ambient/dust2/rockfall_02.vsnd', 'sounds/ambient/dust2/rockfall_03.vsnd', 'sounds/ambient/dust2/rockfall_04.vsnd', 'sounds/ambient/dust2/rockfall_05.vsnd', 'sounds/ambient/dust2/rockfall_06.vsnd', 'sounds/ambient/dust2/rockfall_07.vsnd', 'sounds/ambient/dust2/rockfall_08.vsnd']}, 'ambient_example.indoors.vent': {'base': 'amb.looping.atXYZ.base', 'volume': 0.2, 'position': [1136.0, 1392.0, 64.0], 'vsnd_files_track_01': 'sounds/vent_01.vsnd', 'distance_volume_mapping_curve': [[0.0, 1.0, 0.0, 0.0, 2.0, 3.0], [500.0, 1.0, 0.0, 0.0, 2.0, 3.0]]}}

data_kv3 = {"""
<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
	"ambient_example.indoors.rockfalls" = 
	{
		base = "amb.intermittent.randomAroundPlayer.base"
		volume = 0.7
		randomize_position_min_radius = 500.0
		randomize_position_max_radius = 1000.0
		randomize_position_hemisphere = false
		retrigger_interval_min = 5.0
		retrigger_interval_max = 15.0
		retrigger_radius = 1000.0
		vsnd_files_track_01 = 
		[
			"sounds/ambient/dust2/rockfall_01.vsnd",
			"sounds/ambient/dust2/rockfall_02.vsnd",
			"sounds/ambient/dust2/rockfall_03.vsnd",
			"sounds/ambient/dust2/rockfall_04.vsnd",
			"sounds/ambient/dust2/rockfall_05.vsnd",
			"sounds/ambient/dust2/rockfall_06.vsnd",
			"sounds/ambient/dust2/rockfall_07.vsnd",
			"sounds/ambient/dust2/rockfall_08.vsnd",
		]
	}
	"ambient_example.indoors.vent" = 
	{
		base = "amb.looping.atXYZ.base"
		volume = 0.2
		position = [ 1136.0, 1392.0, 64.0 ]
		vsnd_files_track_01 = "sounds/vent_01.vsnd"
		distance_volume_mapping_curve = 
		[
			[
				0.0, 1.0, 0.0, 0.0,
				2.0, 3.0,
			],
			[
				500.0, 1.0, 0.0, 0.0,
				2.0, 3.0,
			],
		]
	}
}
"""
}

square_brackets_group = ['m_Children', 'm_Variables', 'm_Modifiers', 'm_vRandomRotationMin', 'm_vRandomRotationMax', 'm_vPosition']