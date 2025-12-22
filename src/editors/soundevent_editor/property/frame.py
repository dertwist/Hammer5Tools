import ast

from PySide6.QtWidgets import QWidget, QHBoxLayout, QApplication, QTreeWidget
from PySide6.QtCore import Signal

from src.editors.soundevent_editor.objects import mixgroup_objects, dsp_preset_objects, type_objects
from src.editors.soundevent_editor.property.common import SoundEventEditorPropertyList
from src.editors.soundevent_editor.property.ui_frame import Ui_Form
from src.property.methods import PropertyMethods
from src.common import convert_snake_case
from src.settings.main import debug
from src.editors.soundevent_editor.common import vsnd_filepath_convert


class SoundEventEditorPropertyFrame(QWidget):
    """PropertyFrame suppose to collect properties and gives dict value"""
    edited = Signal()
    def __init__(self, _data: dict = None, widget_list: QHBoxLayout = None, tree:QTreeWidget = None):
        """Data variable is _data:d can receive only dict value"""
        super().__init__()

        # If dict value is empty, just skip initialization of the frame and delete item itself
        if widget_list is None:
            raise ValueError
        if _data is None:
            self.deleteLater()
        else:
            # Init UI file
            self.ui = Ui_Form()
            self.ui.setupUi(self)
            self.setAcceptDrops(True)

            # Variables
            self.tree = tree
            self.value = dict()
            self.name = str(next(iter(_data)))
            self.widget_list = widget_list
            self._height = 24

            # Populate
            self.populate_properties(data=_data)

            # Init
            self.init_connections()
            self.init_header()

            # Update data
            self.on_property_updated()

    def init_connections(self):
        """Adding connections to the buttons"""
        self.ui.show_child.clicked.connect(self.show_child_action)
        self.ui.delete_button.clicked.connect(self.delete_action)
        self.ui.copy_button.clicked.connect(self.copy_action)
    def init_header(self):
        """Setup for header frame"""
        self.ui.property_class.setText(convert_snake_case(self.name))

    #=============================================================<  Properties  >===========================================================

    def add_property(self, name: str, value:str):
        """
        Adding a property to the frame widget.
        Import properties classes form another file
        """
        # Convert value str to dict
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except Exception as error:
                debug(error)

        # Widgets import
        from src.editors.soundevent_editor.property.common import (
            SoundEventEditorPropertyFloat,
            SoundEventEditorPropertyLegacy,
            SoundEventEditorPropertyBool,
            SoundEventEditorPropertyVector3,
            SoundEventEditorPropertyFiles,
            SoundEventEditorPropertySoundEvent,
            SoundEventEditorPropertyCombobox,
            SoundEventEditorPropertyBaseLegacy
        )
        from src.editors.soundevent_editor.property.curve.main import SoundEventEditorPropertyCurve

        # Float (Only Positive)
        if name == 'volume':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'delay':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'pitch':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'retrigger_interval_min':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'retrigger_interval_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'occlusion_intensity':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'distance_effect_mix':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'reverb_wet':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'occlusion_frequency_scale':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'vsnd_duration':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'retrigger_radius':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 200], only_positive=True, value=value)
        # New Float Properties (Only Positive)
        elif name == 'block_duration':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'block_distance':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'instance_limit':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 100], only_positive=True, value=value)
        elif name == 'reverb_source_wet':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'distance_multiplier':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'broadcast_distance_override':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'block_other_duration':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'block_other_distance':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'velocity_volume_seek_speed':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 2000], only_positive=True, value=value)
        elif name == 'ducking_bypass':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'self_destruct_time':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 100], only_positive=True, value=value)
        elif name == 'value':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'dsp_bypass':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'occlusion_interval':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'dsp_blend':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'voice_culling_threshold':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1], only_positive=True, value=value)
        elif name == 'volume_fade_out_input_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'priority':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'volume_fade_initial_input_min':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 100], only_positive=True, value=value)
        elif name == 'volume_fade_initial_input_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 100], only_positive=True, value=value)
        elif name == 'volume_fade_initial_input_map_min':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'volume_fade_initial_input_map_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'startpoint_01':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'startpoint_02':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'startpoint_03':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'endpoint_01':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'endpoint_02':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'endpoint_03':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'sync_action_to_startround':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=True, value=value)
        elif name == 'stop_at_time':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 100], only_positive=True, value=value)
        elif name == 'restart_startpoint_01':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)
        elif name == 'restart_startpoint_02':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 1000], only_positive=True, value=value)

        # Float
        elif name == 'volume_random_min':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=False, value=value)
        elif name == 'volume_random_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=False, value=value)
        elif name == 'pitch_random_min':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=False, value=value)
        elif name == 'pitch_random_max':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 10], only_positive=False, value=value)
        elif name == 'randomize_position_min_radius':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[-200, 200], only_positive=False, value=value)
        elif name == 'randomize_position_max_radius':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[-200, 200], only_positive=False, value=value)
        elif name == 'retrigger_count':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[-10, 100], only_positive=False, value=value)
        # Int

        # Bool
        elif name == 'enable_child_events':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'enable_retrigger':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'restrict_source_reverb':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'randomize_position_hemisphere':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_distance_unfiltered_stereo_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_distance_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_time_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'override_dsp_preset':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'set_child_position':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'position_relative_to_player':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_world_position':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        # New Bool Properties
        elif name == 'block_matching_events':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'block_match_entity':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_fadetime_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_entity_position_if_local_player':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'display_broadcast':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_baked_occlusion':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'occlusion':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'preload_vsnds':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_impact_speed_input_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'set_mixlayer_amount_enable':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'block_other':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_velocity_volume_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_velocity_eq':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_volume_convar':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'vsnd_pause_with_game':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'is_ui_sound':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_uiposition':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'position_offset_relative':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_time_unfiltered_stereo_mapping_curve':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        elif name == 'use_doppler':
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=value)
        # String-based Bool Properties (these use string 'true'/'false' instead of boolean)
        elif name in ['stop_selection_music', 'stop_all_non_music', 'stop_music', 'stop_match_end', 'stop_loading', 
                      'join_non_mvp_group', 'priority_override', 'loop_track', 'should_queue_track', 
                      'update_track_syncpoint_index', 'stop_start_round', 'stop_tensec_count', 'stop_bomb_planted', 
                      'stop_got_hostage', 'stop_music_except_mvp', 'skip_if_muted', 'test_mvp_block', 
                      'check_for_classic_deathcam', 'stop_won_mvp', 'block_won_lost']:
            # Convert string 'true'/'false' to boolean for the UI
            bool_value = value == 'true' if isinstance(value, str) else bool(value)
            self.property_instance = SoundEventEditorPropertyBool(label_text=name, value=bool_value)
        
        # Curve
        elif name == 'distance_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=["Distance", "Volume"])
        elif name == 'distance_unfiltered_stereo_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=["Distance", "Unfiltered Stereo"])
        elif name == 'fadetime_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Fade Time', 'Volume'])
        elif name == 'time_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Time', 'Volume'])
        # New Curve Properties
        elif name == 'impact_speed_input_volume_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Impact Speed', 'Volume'])
        elif name == 'time_mixlayer_amount_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Time', 'Mixlayer Amount'])
        elif name == 'velocity_volume_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Velocity', 'Volume'])
        elif name == 'time_unfiltered_stereo_mapping_curve':
            self.property_instance = SoundEventEditorPropertyCurve(label_text=name, value=value, labels=['Time', 'Unfiltered Stereo'])
        
        # Combobox
        elif name == 'base':
            self.property_instance = SoundEventEditorPropertyBaseLegacy(label_text=name, value=value, tree=self.tree, objects=[])
        elif name == 'mixgroup':
            self.property_instance = SoundEventEditorPropertyCombobox(label_text=name, value=value, tree=self.tree, objects=mixgroup_objects)
        elif name == 'dsp_preset':
            self.property_instance = SoundEventEditorPropertyCombobox(label_text=name, value=value, tree=self.tree, objects=dsp_preset_objects)
        elif name == 'type':
            self.property_instance = SoundEventEditorPropertyCombobox(label_text=name, value=value, tree=self.tree, objects=type_objects)
        # New String/Combobox Properties (using Legacy for now as they are text fields)
        elif name in ['metadata', 'source_soundscape', 'set_mixlayer_layer', 'block_other_name', 'volume_convar', 'mixlayer_name']:
            self.property_instance = SoundEventEditorPropertyLegacy(label_text=name, value=value)
        
        # Vector3
        elif name == 'position':
            self.property_instance = SoundEventEditorPropertyVector3(label_text=name, value=value)
        elif name == 'position_offset':
            self.property_instance = SoundEventEditorPropertyVector3(label_text=name, value=value)
        
        # List/Files
        elif name == 'vsnd_files_track_01':
            self.property_instance = SoundEventEditorPropertyFiles(label_text=name, value=value)
        elif name == 'vsnd_files':
            self.property_instance = SoundEventEditorPropertyFiles(label_text=name, value=value)
        elif name == 'soundevent_01':
            self.property_instance = SoundEventEditorPropertySoundEvent(label_text=name, value=value, tree=self.tree)
        # Array Properties (syncpoints) - using Legacy for now
        elif name in ['syncpoints_01', 'syncpoints_02', 'syncpoints_03']:
            self.property_instance = SoundEventEditorPropertyLegacy(label_text=name, value=value)
        
        # Legacy
        else:
            self.property_instance = SoundEventEditorPropertyLegacy(label_text=name,value=value)
        self.property_instance.edited.connect(self.on_property_updated)
        self.ui.content.layout().addWidget(self.property_instance)
    def on_property_updated(self):
        """If some of the properties were changed send signa with dict value"""
        self.value = self.serialize_properties()
        self.edited.emit()

    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        debug(f"populate_properties frame Data: \n {data}")
        if data:
            for name, value in data.items():
                self.add_property(name, value)
    def serialize_properties(self):
        """Geather all values into dict value"""
        _data = {}
        if _data is None:
            pass
        else:
            for index in range(self.ui.content.layout().count()):
                widget_instance = self.ui.content.layout().itemAt(index).widget()
                value_dict = widget_instance.value
                _data.update(value_dict)
            debug(f"serialize_properties frame Data: \n {_data}")
            return _data

    def get_property(self, index):
        """Getting single property from the frame widget"""
        pass
    def deserialize_property(self, _data: dict = None):
        """Deserialize property from json"""

    #==============================================================<  Actions  >============================================================

    def copy_action(self):
        """Copy action"""
        clipboard = QApplication.clipboard()
        _data = self.serialize_properties()
        _data = str(_data)
        clipboard.setText(_data)

    def delete_action(self):
        """Set value to None, then send signal that updates value then delete self"""
        for index in range(self.ui.content.layout().count()):
            widget_instance = self.ui.content.layout().itemAt(index).widget()
            widget_instance.deleteLater()
        self.value = None
        self.edited.emit()
        self.deleteLater()


    def show_child_action(self):
        """Showing child widgets, resizes the layout to hide or show child"""
        if not self.ui.show_child.isChecked():
            self.ui.content.setMaximumHeight(0)
        else:
            self.ui.content.setMaximumHeight(16666)

    #===========================================================<  Drag and drop  >=========================================================

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)

                widget: SoundEventEditorPropertyFrame = self.widget_list.layout().itemAt(target_index).widget()
                widget_property = widget.ui.content.layout().itemAt(0).widget()
                if isinstance(widget_property, SoundEventEditorPropertyList):
                    urls = mime_data.urls()
                    url_set = set(url.toString() for url in urls)
                    for url in url_set:
                        __value = url.replace("file:///", "")
                        __value = vsnd_filepath_convert(__value)
                        widget_property.add_element(__value)

                elif source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)

        event.accept()