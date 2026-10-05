"""Canonical schema for every SoundEvent property the editor can build.

One table drives three things that used to be spread out or absent:

* which widget class ``property/frame.py`` builds and with what arguments,
* which group a property is displayed under and in what order,
* which toggle a property depends on.

Dict order is display order: groups follow ``GROUPS``, properties follow their
order inside this table. There is no separate order field to keep in sync.

Kept free of Qt imports so it can be read and tested without a QApplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gui.editors.soundevent_editor.objects import (
    dsp_preset_objects,
    mixgroup_objects,
    type_objects,
)

# Display title per group, in display order. 'custom' collects keys with no
# spec; 'advanced' holds fields that are valid but rarely tuned by hand.
GROUPS: tuple[tuple[str, str], ...] = (
    ("general", "General"),
    ("playback", "Playback"),
    ("fade", "Fade"),
    ("position", "Position"),
    ("distance_curves", "Distance Curves"),
    ("time_curves", "Time Curves"),
    ("velocity", "Velocity & Doppler"),
    ("occlusion", "Occlusion & Reverb"),
    ("dsp", "DSP"),
    ("children", "Child Events"),
    ("retrigger", "Retrigger"),
    ("limits", "Limits & Blocking"),
    ("mixer", "Mixer & Convar"),
    ("music", "Music"),
    ("files", "Audio Files"),
    ("advanced", "Advanced"),
    ("custom", "Custom"),
)

# Groups that start collapsed. Advanced fields are real but rarely hand-tuned,
# and every unrecognised key lands in custom, so neither should push the
# common properties off screen.
COLLAPSED_BY_DEFAULT: frozenset[str] = frozenset({"advanced", "custom"})

GROUP_ORDER: dict[str, int] = {name: index for index, (name, _) in enumerate(GROUPS)}
GROUP_TITLES: dict[str, str] = dict(GROUPS)


@dataclass(frozen=True)
class PropertySpec:
    """How one property is built and where it is shown."""

    kind: str
    group: str
    options: dict = field(default_factory=dict)


SPECS: dict[str, PropertySpec] = {
    # -- general --
    'comment': PropertySpec('comment', 'general'),
    'type': PropertySpec('combobox', 'general', options=dict(objects=type_objects)),
    'base': PropertySpec('base', 'general', options=dict(objects=[])),
    'metadata': PropertySpec('legacy', 'general'),
    'value': PropertySpec('float', 'general', options=dict(slider_range=[0, 10], only_positive=True)),
    'vsnd_duration': PropertySpec('float', 'general', options=dict(slider_range=[0, 10], only_positive=True)),
    # -- playback --
    'volume': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=True)),
    'volume_random_min': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=False)),
    'volume_random_max': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=False)),
    'pitch': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=True)),
    'pitch_random_min': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=False)),
    'pitch_random_max': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=False)),
    'delay': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=True)),
    'priority': PropertySpec('float', 'playback', options=dict(slider_range=[0, 10], only_positive=True)),
    'ducking_bypass': PropertySpec('float', 'playback', options=dict(slider_range=[0, 1], only_positive=True)),
    'preload_vsnds': PropertySpec('bool', 'playback'),
    'vsnd_pause_with_game': PropertySpec('bool', 'playback'),
    'is_ui_sound': PropertySpec('bool', 'playback'),
    'voice_culling_threshold': PropertySpec('float', 'playback', options=dict(slider_range=[0, 1], only_positive=True)),
    # -- fade --
    'use_fadetime_volume_mapping_curve': PropertySpec('bool', 'fade'),
    'fadetime_volume_mapping_curve': PropertySpec('curve', 'fade', options=dict(labels=['Fade Time', 'Volume'])),
    'volume_fade_out_input_max': PropertySpec('float', 'fade', options=dict(slider_range=[0, 10], only_positive=True)),
    'volume_fade_initial_input_min': PropertySpec('float', 'fade', options=dict(slider_range=[0, 100], only_positive=True)),
    'volume_fade_initial_input_max': PropertySpec('float', 'fade', options=dict(slider_range=[0, 100], only_positive=True)),
    'volume_fade_initial_input_map_min': PropertySpec('float', 'fade', options=dict(slider_range=[0, 10], only_positive=True)),
    'volume_fade_initial_input_map_max': PropertySpec('float', 'fade', options=dict(slider_range=[0, 10], only_positive=True)),
    # -- position --
    'position': PropertySpec('vector3', 'position', options=dict(slider_range=[-1000, 1000])),
    'position_offset': PropertySpec('vector3', 'position', options=dict(slider_range=[-1000, 1000])),
    'position_offset_relative': PropertySpec('bool', 'position'),
    'use_world_position': PropertySpec('bool', 'position'),
    'use_uiposition': PropertySpec('bool', 'position'),
    'position_relative_to_player': PropertySpec('bool', 'position'),
    'use_entity_position_if_local_player': PropertySpec('bool', 'position'),
    'set_child_position': PropertySpec('bool', 'position'),
    'randomize_position_min_radius': PropertySpec('float', 'position', options=dict(slider_range=[-200, 200], only_positive=False)),
    'randomize_position_max_radius': PropertySpec('float', 'position', options=dict(slider_range=[-200, 200], only_positive=False)),
    'randomize_position_hemisphere': PropertySpec('bool', 'position'),
    'distance_multiplier': PropertySpec('float', 'position', options=dict(slider_range=[0, 10], only_positive=True)),
    'broadcast_distance_override': PropertySpec('float', 'position', options=dict(slider_range=[0, 1000], only_positive=True)),
    'display_broadcast': PropertySpec('bool', 'position'),
    # -- distance_curves --
    'use_distance_volume_mapping_curve': PropertySpec('bool', 'distance_curves'),
    'distance_volume_mapping_curve': PropertySpec('curve', 'distance_curves', options=dict(labels=['Distance', 'Volume'])),
    'use_distance_unfiltered_stereo_mapping_curve': PropertySpec('bool', 'distance_curves'),
    'distance_unfiltered_stereo_mapping_curve': PropertySpec('curve', 'distance_curves', options=dict(labels=['Distance', 'Unfiltered Stereo'])),
    # -- time_curves --
    'use_time_volume_mapping_curve': PropertySpec('bool', 'time_curves'),
    'time_volume_mapping_curve': PropertySpec('curve', 'time_curves', options=dict(labels=['Time', 'Volume'])),
    'use_time_unfiltered_stereo_mapping_curve': PropertySpec('bool', 'time_curves'),
    'time_unfiltered_stereo_mapping_curve': PropertySpec('curve', 'time_curves', options=dict(labels=['Time', 'Unfiltered Stereo'])),
    # -- velocity --
    'use_doppler': PropertySpec('bool', 'velocity'),
    'use_velocity_volume_curve': PropertySpec('bool', 'velocity'),
    'velocity_volume_curve': PropertySpec('curve', 'velocity', options=dict(labels=['Velocity', 'Volume'])),
    'velocity_volume_seek_speed': PropertySpec('float', 'velocity', options=dict(slider_range=[0, 2000], only_positive=True)),
    'use_velocity_eq': PropertySpec('bool', 'velocity'),
    'use_impact_speed_input_volume_mapping_curve': PropertySpec('bool', 'velocity'),
    'impact_speed_input_volume_mapping_curve': PropertySpec('curve', 'velocity', options=dict(labels=['Impact Speed', 'Volume'])),
    # -- occlusion --
    'occlusion': PropertySpec('bool', 'occlusion'),
    'occlusion_intensity': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 10], only_positive=True)),
    'occlusion_frequency_scale': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 1], only_positive=True)),
    'occlusion_interval': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 1], only_positive=True)),
    'use_baked_occlusion': PropertySpec('bool', 'occlusion'),
    'distance_effect_mix': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 10], only_positive=True)),
    'reverb_wet': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 1], only_positive=True)),
    'reverb_source_wet': PropertySpec('float', 'occlusion', options=dict(slider_range=[0, 1], only_positive=True)),
    'restrict_source_reverb': PropertySpec('bool', 'occlusion'),
    # -- dsp --
    'dsp_preset': PropertySpec('combobox', 'dsp', options=dict(objects=dsp_preset_objects)),
    'override_dsp_preset': PropertySpec('bool', 'dsp'),
    'dsp_blend': PropertySpec('float', 'dsp', options=dict(slider_range=[0, 1], only_positive=True)),
    'dsp_bypass': PropertySpec('float', 'dsp', options=dict(slider_range=[0, 1], only_positive=True)),
    # -- children --
    'enable_child_events': PropertySpec('bool', 'children'),
    'soundevent_01': PropertySpec('soundevent', 'children'),
    # -- retrigger --
    'enable_retrigger': PropertySpec('bool', 'retrigger'),
    'retrigger_interval_min': PropertySpec('float', 'retrigger', options=dict(slider_range=[0, 10], only_positive=True)),
    'retrigger_interval_max': PropertySpec('float', 'retrigger', options=dict(slider_range=[0, 10], only_positive=True)),
    'retrigger_radius': PropertySpec('float', 'retrigger', options=dict(slider_range=[0, 200], only_positive=True)),
    'retrigger_count': PropertySpec('float', 'retrigger', options=dict(slider_range=[-10, 100], only_positive=False)),
    # -- limits --
    'instance_limit': PropertySpec('float', 'limits', options=dict(slider_range=[0, 100], only_positive=True)),
    'self_destruct_time': PropertySpec('float', 'limits', options=dict(slider_range=[0, 100], only_positive=True)),
    'stop_at_time': PropertySpec('float', 'limits', options=dict(slider_range=[0, 100], only_positive=True)),
    'block_matching_events': PropertySpec('bool', 'limits'),
    'block_match_entity': PropertySpec('bool', 'limits'),
    'block_duration': PropertySpec('float', 'limits', options=dict(slider_range=[0, 10], only_positive=True)),
    'block_distance': PropertySpec('float', 'limits', options=dict(slider_range=[0, 1000], only_positive=True)),
    'block_other': PropertySpec('bool', 'limits'),
    'block_other_name': PropertySpec('legacy', 'limits'),
    'block_other_duration': PropertySpec('float', 'limits', options=dict(slider_range=[0, 10], only_positive=True)),
    'block_other_distance': PropertySpec('float', 'limits', options=dict(slider_range=[0, 1000], only_positive=True)),
    # -- mixer --
    'mixgroup': PropertySpec('combobox', 'mixer', options=dict(objects=mixgroup_objects)),
    'mixlayer_name': PropertySpec('legacy', 'mixer'),
    'set_mixlayer_layer': PropertySpec('legacy', 'mixer'),
    'set_mixlayer_amount_enable': PropertySpec('bool', 'mixer'),
    'time_mixlayer_amount_curve': PropertySpec('curve', 'mixer', options=dict(labels=['Time', 'Mixlayer Amount'])),
    'use_volume_convar': PropertySpec('bool', 'mixer'),
    'volume_convar': PropertySpec('legacy', 'mixer'),
    # -- music --
    'loop_track': PropertySpec('string_bool', 'music'),
    'should_queue_track': PropertySpec('string_bool', 'music'),
    'update_track_syncpoint_index': PropertySpec('string_bool', 'music'),
    'sync_action_to_startround': PropertySpec('float', 'music', options=dict(slider_range=[0, 10], only_positive=True)),
    'startpoint_01': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'startpoint_02': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'startpoint_03': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'endpoint_01': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'endpoint_02': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'endpoint_03': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'restart_startpoint_01': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'restart_startpoint_02': PropertySpec('float', 'music', options=dict(slider_range=[0, 1000], only_positive=True)),
    'syncpoints_01': PropertySpec('legacy', 'music'),
    'syncpoints_02': PropertySpec('legacy', 'music'),
    'syncpoints_03': PropertySpec('legacy', 'music'),
    'stop_selection_music': PropertySpec('string_bool', 'music'),
    'stop_all_non_music': PropertySpec('string_bool', 'music'),
    'stop_music': PropertySpec('string_bool', 'music'),
    'stop_match_end': PropertySpec('string_bool', 'music'),
    'stop_loading': PropertySpec('string_bool', 'music'),
    'join_non_mvp_group': PropertySpec('string_bool', 'music'),
    'priority_override': PropertySpec('string_bool', 'music'),
    'stop_start_round': PropertySpec('string_bool', 'music'),
    'stop_tensec_count': PropertySpec('string_bool', 'music'),
    'stop_bomb_planted': PropertySpec('string_bool', 'music'),
    'stop_got_hostage': PropertySpec('string_bool', 'music'),
    'stop_music_except_mvp': PropertySpec('string_bool', 'music'),
    'skip_if_muted': PropertySpec('string_bool', 'music'),
    'test_mvp_block': PropertySpec('string_bool', 'music'),
    'check_for_classic_deathcam': PropertySpec('string_bool', 'music'),
    'stop_won_mvp': PropertySpec('string_bool', 'music'),
    'block_won_lost': PropertySpec('string_bool', 'music'),
    # -- files --
    'vsnd_files': PropertySpec('files', 'files'),
    'vsnd_files_track_01': PropertySpec('files', 'files'),
    # -- advanced --
    'source_soundscape': PropertySpec('legacy', 'advanced'),
    'uiposition': PropertySpec('vector3', 'advanced', options=dict(slider_range=[-1000, 1000])),
    'use_distance_pitch_mapping_curve': PropertySpec('bool', 'advanced'),
    'distance_pitch_mapping_curve': PropertySpec('curve', 'advanced', options=dict(labels=['Distance', 'Pitch'])),
    'occlusion_path_curve': PropertySpec('curve', 'advanced', options=dict(labels=['Distance', 'Occlusion'])),
    'doppler_factor': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 10], only_positive=True)),
    'doppler_factor_receding': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 10], only_positive=True)),
    'impact_speed_input': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 1000], only_positive=True)),
    'velocity_magnitude': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 2000], only_positive=True)),
    'voice_fade_out_time': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 10], only_positive=True)),
    'voice_looped_culling_update_time': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 10], only_positive=True)),
    'randomize_start_time': PropertySpec('bool', 'advanced'),
    'restart_startpoint_03': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 1000], only_positive=True)),
    'retrigger_keepalive_override': PropertySpec('float', 'advanced', options=dict(slider_range=[0, 10], only_positive=True)),
}

_INDEX: dict[str, int] = {key: index for index, key in enumerate(SPECS)}

# A toggle and the properties it governs. Dependents are disabled while the
# toggle is off; they are never removed, so their values still round-trip.
TOGGLE_DEPENDENTS: dict[str, tuple[str, ...]] = {
    "use_distance_volume_mapping_curve": ("distance_volume_mapping_curve",),
    "use_distance_unfiltered_stereo_mapping_curve": (
        "distance_unfiltered_stereo_mapping_curve",
    ),
    "use_distance_pitch_mapping_curve": ("distance_pitch_mapping_curve",),
    "use_time_volume_mapping_curve": ("time_volume_mapping_curve",),
    "use_time_unfiltered_stereo_mapping_curve": ("time_unfiltered_stereo_mapping_curve",),
    "use_fadetime_volume_mapping_curve": ("fadetime_volume_mapping_curve",),
    "use_velocity_volume_curve": ("velocity_volume_curve", "velocity_volume_seek_speed"),
    "use_impact_speed_input_volume_mapping_curve": (
        "impact_speed_input_volume_mapping_curve",
        "impact_speed_input",
    ),
    "use_baked_occlusion": ("occlusion_path_curve",),
    "use_doppler": ("doppler_factor", "doppler_factor_receding"),
    "use_volume_convar": ("volume_convar",),
    "use_uiposition": ("uiposition",),
    "override_dsp_preset": ("dsp_preset", "dsp_blend"),
    "enable_child_events": ("soundevent_01",),
    "enable_retrigger": (
        "retrigger_interval_min",
        "retrigger_interval_max",
        "retrigger_radius",
        "retrigger_count",
        "retrigger_keepalive_override",
    ),
    "block_other": ("block_other_name", "block_other_duration", "block_other_distance"),
    "block_matching_events": ("block_match_entity", "block_duration", "block_distance"),
    "set_mixlayer_amount_enable": ("set_mixlayer_layer", "time_mixlayer_amount_curve"),
}

# Min/max pairs shown under one header instead of two. Both keys must be
# present on the event for the pair to be used.
PAIRED: tuple[tuple[str, str, str], ...] = (
    ("volume_random_min", "volume_random_max", "Volume Random"),
    ("pitch_random_min", "pitch_random_max", "Pitch Random"),
    ("retrigger_interval_min", "retrigger_interval_max", "Retrigger Interval"),
    ("randomize_position_min_radius", "randomize_position_max_radius", "Randomize Position Radius"),
    ("volume_fade_initial_input_min", "volume_fade_initial_input_max", "Volume Fade Initial Input"),
    (
        "volume_fade_initial_input_map_min",
        "volume_fade_initial_input_map_max",
        "Volume Fade Initial Input Map",
    ),
)


def get_spec(key: str) -> PropertySpec:
    """Spec for a property key. Unknown keys become free-form custom entries.

    Repeatable comments (comment_2, comment_3) resolve to the comment spec.
    """
    spec = SPECS.get(key)
    if spec is not None:
        return spec
    if isinstance(key, str) and key.startswith("comment_"):
        return SPECS["comment"]
    return PropertySpec("legacy", "custom")


def sort_key(key: str) -> tuple[int, int]:
    """Display position of a property: (group index, index within this table)."""
    spec = get_spec(key)
    return GROUP_ORDER[spec.group], _INDEX.get(key, len(SPECS))
