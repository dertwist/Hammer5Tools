from src.settings.main import debug
from src.editors.smartprop_editor.ui_property_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Signal, Qt, QTimer, QThreadPool
from PySide6.QtGui import QAction

from src.property.methods import PropertyMethods
from src.widgets.popup_menu.main import PopupMenu
from src.widgets.element_id import ElementIDGenerator

from src.editors.smartprop_editor.property.legacy import PropertyLegacy
from src.editors.smartprop_editor.property.vector3d import PropertyVector3D
from src.editors.smartprop_editor.property.float import PropertyFloat
from src.editors.smartprop_editor.property.bool import PropertyBool
from src.editors.smartprop_editor.property.combobox import PropertyCombobox
from src.editors.smartprop_editor.property.string import PropertyString
from src.editors.smartprop_editor.property.color import PropertyColor
from src.editors.smartprop_editor.property.comparison import PropertyComparison
from src.editors.smartprop_editor.property.filtersurface import PropertySurface
from src.editors.smartprop_editor.property.colormatch import PropertyColorMatch
from src.editors.smartprop_editor.property.material_replacements import PropertyMaterialReplacements
from src.editors.smartprop_editor.property.variable import PropertyVariableOutput
from src.editors.smartprop_editor.property.set_variable import PropertyVariableValue
from src.editors.smartprop_editor.property.comment import PropertyComment
from src.editors.smartprop_editor.property.reference import PropertyReference
from PySide6.QtGui import QCursor
from src.widgets import HierarchyItemModel
import uuid

import ast

from src.widgets import exception_handler
from src.editors.smartprop_editor.property_data_worker import (
    PropertyDataWorker,
)

class PropertyFrame(QWidget):
    edited = Signal()
    slider_pressed = Signal()
    committed = Signal()

    # A lookup dictionary to avoid multiple if/elif checks; cached at class level
    _prop_classes_map_cache = {
        # Elements
        'FitOnLine': [
            'm_nReferenceID', 'm_bEnabled', 'm_vStart','m_vEnd', 'm_PointSpace', 'm_bOrientAlongLine', 'm_vUpDirection', 'm_UpDirectionSpace', 'm_bPrioritizeUp', 'm_nScaleMode', 'm_nPickMode'
        ],
        'PickOne': [
            'm_nReferenceID', 'm_bEnabled', 'm_SelectionMode', 'm_SpecificChildIndex', 'm_OutputChoiceVariableName', 'm_bConfigurable', 'm_vHandleOffset', 'm_HandleColor', 'm_HandleSize', 'm_HandleShape'
        ],
        'PlaceInSphere': [
            'm_nReferenceID', 'm_bEnabled', 'm_nCountMin','m_nCountMax','m_flPositionRadiusInner','m_flPositionRadiusOuter', 'm_flRandomness', 'm_bAlignOrientation', 'm_PlacementMode', 'm_DistributionMode', 'm_vAlignDirection', 'm_vPlaneUpDirection'
        ],
        'PlaceOnPath': [
            'm_nReferenceID', 'm_bEnabled', 'm_PathName','m_vPathOffset','m_flOffsetAlongPath','m_PathSpace', 'm_flSpacing', 'm_SpacingSpace', 'm_bContinuousSpline', 'm_DefaultPath', 'm_bUseFixedUpDirection', 'm_bUseProjectedDistance', 'm_UpDirectionSpace', 'm_vUpDirection'
        ],
        'Model': [
            'm_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_bForceStatic', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_nLodLevel', 'm_DetailObjectFadeLevel'
        ],
        'SmartProp': [
            'm_nReferenceID', 'm_bEnabled', 'm_sSmartProp','m_vModelScale'
        ],
        'PlaceMultiple': [
            'm_nReferenceID', 'm_bEnabled', 'm_nCountMin', 'm_nCountMax', 'm_flSpacing', 'm_PlacementMode', 'm_bRandomizeOrder'
        ],
        'Group': [
            'm_nReferenceID', 'm_bEnabled'
        ],
        'ModifyState': [
            'm_nReferenceID', 'm_bEnabled'
        ],
        'BendDeformer': [
            'm_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vSize', 'm_vOrigin', 'm_vAngles', 'm_flBendAngle', 'm_flBendPoint', 'm_flBendRadius'
        ],
        'ModelEntity': [
            'm_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_bDetailObject', 'm_bRigidDeformation', 'm_nLodLevel', 'm_DetailObjectFadeLevel'
        ],
        'PropPhysics': [
            'm_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_vModelScale', 'm_MaterialGroupName', 'm_flMass', 'm_bStartAsleep', 'm_nHealth', 'm_bEnableMotion',
        ],
        'PropDynamic': [
            'm_nReferenceID', 'm_bEnabled', 'm_sModelName', 'm_sAnimationSequence', 'm_sDefaultAnimation', 'm_vModelScale', 'm_MaterialGroupName'
        ],
        'MidpointDeformer': [
            'm_nReferenceID', 'm_bEnabled', 'm_bDeformationEnabled', 'm_vStart', 'm_vEnd', 'm_fRadius', 'm_bContinuousSpline', 'm_vOffset', 'm_vAngles', 'm_vScale', 'm_fFalloff', 'm_OutputVariable'
        ],
        'Layout2DGrid': [
            'm_nReferenceID', 'm_bEnabled', 'm_flWidth', 'm_flLength', 'm_bVerticalLength', 'm_GridArrangement', 'm_GridOriginMode', 'm_nCountW', 'm_nCountL', 'm_flSpacingWidth', 'm_flSpacingLength', 'm_bAlternateShift', 'm_flAlternateShiftWidth', 'm_flAlternateShiftLength'
        ],
        # Operators
        'CreateSizer': [
            'm_bEnabled', 'm_flInitialMinX', 'm_flInitialMaxX', 'm_flConstraintMinX', 'm_flConstraintMaxX',
            'm_OutputVariableMinX', 'm_OutputVariableMaxX', 'm_flInitialMinY', 'm_flInitialMaxY',
            'm_flConstraintMinY', 'm_flConstraintMaxY', 'm_OutputVariableMinY', 'm_OutputVariableMaxY',
            'm_flInitialMinZ', 'm_flInitialMaxZ', 'm_flConstraintMinZ', 'm_flConstraintMaxZ',
            'm_OutputVariableMinZ', 'm_OutputVariableMaxZ'
        ],
        'CreateRotator': [
            'm_bEnabled', 'm_vRotationAxis', 'm_CoordinateSpace', 'm_flDisplayRadius', 'm_bApplyToCurrentTransform',
            'm_OutputVariable', 'm_flSnappingIncrement', 'm_bEnforceLimits', 'm_flMinAngle', 'm_flMaxAngle'
        ],
        'CreateLocator': [
            'm_bEnabled', 'm_flDisplayScale', 'm_bAllowScale'
        ],
        'RestoreState': [
            'm_bEnabled', 'm_StateName', 'm_bDiscardIfUknown'
        ],
        'RandomRotation': [
            'm_bEnabled', 'm_vRandomRotationMin', 'm_vRandomRotationMax'
        ],
        'RandomOffset': [
            'm_bEnabled', 'm_vRandomPositionMin', 'm_vRandomPositionMax'
        ],
        'RandomScale': [
            'm_bEnabled', 'm_flRandomScaleMin', 'm_flRandomScaleMax'
        ],
        'Scale': [
            'm_bEnabled', 'm_flScale'
        ],
        'SetTintColor': [
            'm_bEnabled', 'm_Mode', 'm_ColorChoices', 'm_SelectionMode', 'm_ColorSelection'
        ],
        'MaterialOverride': [
            'm_bEnabled', 'm_bClearCurrentOverrides', 'm_MaterialReplacements'
        ],
        'SetVariable': [
            'm_bEnabled', 'm_VariableValue'
        ],
        # Filters
        'SurfaceProperties': [
            'm_bEnabled', 'm_DisallowedSurfaceProperties', 'm_AllowedSurfaceProperties'
        ],
        'VariableValue': [
            'm_bEnabled', 'm_VariableComparison'
        ],
        'SurfaceAngle': [
            'm_bEnabled', 'm_flSurfaceSlopeMin', 'm_flSurfaceSlopeMax'
        ],
        # Selection Criteria
        'PathPosition': [
            'm_bEnabled', 'm_PlaceAtPositions', 'm_nPlaceEveryNthPosition', 'm_nNthPositionIndexOffset', 'm_bAllowAtStart','m_bAllowAtEnd'
        ],
        'EndCap': [
            'm_bEnabled', 'm_bStart', 'm_bEnd'
        ],
        'LinearLength': [
            'm_bEnabled', 'm_bAllowScale', 'm_flLength', 'm_flMinLength', 'm_flMaxLength'
        ],
        'ChoiceWeight': [
            'm_bEnabled', 'm_flWeight'
        ],
        'TraceInDirection': [
            'm_bEnabled', 'm_DirectionSpace', 'm_nNoHitResult', 'm_flSurfaceUpInfluence', 'm_flOriginOffset', 'm_flTraceLength'
        ],
        'SaveState': [
            'm_bEnabled', 'm_StateName'
        ],
        # Filters / operators used in large modifier stacks (ordered_pairs fast-path)
        'Probability': [
            'm_bEnabled', 'm_flProbability'
        ],
        'Expression': [
            'm_bEnabled', 'm_Expression'
        ],
        'RandomRotationSnapped': [
            'm_bEnabled', 'm_RotationAxes', 'm_flSnapIncrement'
        ],
        'Translate': [
            'm_bEnabled', 'm_vPosition'
        ],
        'Rotate': [
            'm_bEnabled', 'm_vRotation'
        ],
        'Comment': [
            'm_bEnabled', 'm_Comment'
        ],
    }

    # Pre-built ordered_pairs skeletons: (key, None) per known class; worker fills values.
    _ORDERED_PAIRS_CACHE: dict = {}

    # Dedicated pool for property data prep (avoid flooding QThreadPool.globalInstance()).
    _PROPERTY_WORKER_POOL = None

    @classmethod
    def _build_ordered_pairs_cache(cls):
        """Build once at import — same order as reversed(_prop_classes_map_cache[key])."""
        cls._ORDERED_PAIRS_CACHE.clear()
        for prop_class, keys in cls._prop_classes_map_cache.items():
            cls._ORDERED_PAIRS_CACHE[prop_class] = [
                (k, None) for k in reversed(keys)
            ]

    @classmethod
    def _get_worker_pool(cls) -> QThreadPool:
        if cls._PROPERTY_WORKER_POOL is None:
            pool = QThreadPool()
            pool.setMaxThreadCount(4)
            pool.setExpiryTimeout(10_000)
            cls._PROPERTY_WORKER_POOL = pool
        return cls._PROPERTY_WORKER_POOL

    # Keys that must be skipped (no widget created)
    _SKIP_PROPS = frozenset({'m_sLabel', 'm_nElementID', 'm_sReferenceObjectID'})

    # Class-level copy for batch/prewarm workers (same keys as instance only_variable_properties).
    _ONLY_VARIABLE_PROPERTIES = (
        'm_OutputVariableMaxZ',
        'm_OutputVariableMinZ',
        'm_OutputVariableMaxY',
        'm_OutputVariableMinY',
        'm_OutputVariableMaxX',
        'm_OutputVariableMinX',
        'm_OutputVariable',
        'm_OutputChoiceVariableName',
    )

    # Exact-match dispatch: maps value_class -> (WidgetClass, extra_kwargs_dict)
    # PropertyComment is NOT in this dict — handled separately (different signature)
    _EXACT_PROP_DISPATCH = None  # populated lazily by _resolve_dispatch()
    _DISPATCH_RESOLVED = False

    @classmethod
    def _resolve_dispatch(cls):
        if cls._DISPATCH_RESOLVED:
            return

        cls._EXACT_PROP_DISPATCH = {
            'm_bEnabled':              (PropertyBool,                 {}),
            'm_nReferenceID':          (PropertyReference,            {}),
            'm_HandleColor':           (PropertyColor,                {}),
            'm_HandleSize':            (PropertyFloat,                {}),
            'm_ColorChoices':          (PropertyColorMatch,           {}),
            'm_MaterialReplacements':  (PropertyMaterialReplacements, {}),
            'm_flBendPoint':           (PropertyFloat,   {'slider_range': [0, 1]}),
            'm_flWidth':               (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flLength':              (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flSpacingWidth':        (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flSpacingLength':       (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flAlternateShiftWidth': (PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_flAlternateShiftLength':(PropertyFloat,   {'slider_range': [0, 4096]}),
            'm_nCountW':               (PropertyFloat,   {'int_bool': True, 'slider_range': [0, 256]}),
            'm_nCountL':               (PropertyFloat,   {'int_bool': True, 'slider_range': [0, 256]}),
            'm_SpecificChildIndex':    (PropertyFloat,   {'int_bool': True}),
            'm_ColorSelection':        (PropertyFloat,   {'int_bool': True}),
            'm_MaterialGroupName':     (PropertyString,  {'expression_bool': False, 'placeholder': 'Material group name'}),
            'm_Expression':            (PropertyString,  {'expression_bool': True,  'placeholder': 'Expression example: var_bool ? var_sizer * var_multiply'}),
            'm_StateName':             (PropertyString,  {'expression_bool': False, 'only_string': True, 'placeholder': 'State name'}),
            'm_VariableName':          (PropertyString,  {'expression_bool': False, 'only_string': False, 'only_variable': True,
                                                           'force_variable': True, 'placeholder': 'Variable name',
                                                           'filter_types': ['String','Int','Float','Bool']}),
        }

        cls._DISPATCH_RESOLVED = True

    @staticmethod
    def _is_complete_precomputed_payload(prepared) -> bool:
        """Batch/worker dict must have every key _apply_precomputed_payload needs."""
        if prepared is None or not isinstance(prepared, dict):
            return False
        need = (
            "value",
            "ordered_pairs",
            "name_prefix",
            "name",
            "element_id",
            "prop_class",
        )
        if not all(k in prepared for k in need):
            return False
        if not isinstance(prepared.get("value"), dict):
            return False
        op = prepared.get("ordered_pairs")
        if not isinstance(op, list):
            return False
        return True

    def __init__(
        self,
        value,
        widget_list,
        variables_scrollArea,
        element_id_generator,
        element=False,
        tree_hierarchy=None,
        precomputed=None,
    ):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.variables_scrollArea = variables_scrollArea
        self.element = element
        if tree_hierarchy is None:
            raise ValueError("tree_hierarchy cannot be None - a valid hierarchy structure is required")
        else:
            self.tree_hierarchy = tree_hierarchy

        self.element_id_generator = element_id_generator

        self.layout = self.ui.layout

        self.widget_list = widget_list

        if self.element:
            self.ui.copy_button.deleteLater()
            self.ui.delete_button.deleteLater()
        else:
            self.ui.copy_button.clicked.connect(self.copy_action)
            self.ui.delete_button.clicked.connect(self.delete_action)

        self.only_variable_properties = list(self._ONLY_VARIABLE_PROPERTIES)

        # Worker result storage
        self._ordered_pairs = None
        self._worker_signals = None
        self._worker_generation = 0
        # PySide6 often cannot disconnect(bound_method) reliably; connect once per frame.
        self._show_child_signal_connected = False
        self._context_menu_signal_connected = False

        if self._is_complete_precomputed_payload(precomputed):
            self._apply_precomputed_payload(precomputed)
            QTimer.singleShot(0, self._finish_init)
        else:
            # Use ast.literal_eval only if not already a dict
            if not isinstance(value, dict):
                value = ast.literal_eval(value)

            # Keep a raw payload containing '_class' for the worker thread.
            self._worker_raw_value_with_class = dict(value)

            if "_class" not in value:
                raise ValueError(
                    "PropertyFrame value dict missing '_class' and no valid precomputed payload"
                )

            self.name_prefix, self.name = value['_class'].split('_', 1)
            del value['_class']
            self.value = {'m_bEnabled': True}
            self.value.update(value)

            #===========================================================<  Element ID  >========================================================
            self.element_id_generator.update_value(self.value)
            self.element_id = self.element_id_generator.get_key(self.value)
            debug(f'Property frame get_ElementID: {self.element_id}')
            self.ui.element_id_display.setText(str(self.element_id))
            if isinstance(self._worker_raw_value_with_class, dict):
                self._worker_raw_value_with_class['m_nElementID'] = self.element_id

            self.prop_class = self.name
            self.ui.property_class.setText(self.name)

            self._start_data_worker()

    def _apply_precomputed_payload(self, prepared_data: dict):
        """Apply worker/batch-prepared fields; no background worker."""
        self.value = dict(prepared_data["value"])
        self.name_prefix = prepared_data["name_prefix"]
        self.name = prepared_data["name"]
        self.element_id = prepared_data["element_id"]
        self.prop_class = prepared_data["prop_class"]
        self._ordered_pairs = prepared_data["ordered_pairs"]
        self.value["m_nElementID"] = self.element_id
        debug(f'Property frame get_ElementID (precomputed): {self.element_id}')
        self.ui.element_id_display.setText(str(self.element_id))
        self.ui.property_class.setText(self.name)
        self._worker_raw_value_with_class = dict(self.value)
        self._worker_raw_value_with_class["_class"] = f"{self.name_prefix}_{self.name}"

    def _finish_init(self):
        """
        Phase 1: populate the first 4 property widgets immediately for fast
        perceived response. The remaining properties are deferred 30ms.
        on_edited() is NOT called here — the value dict is incomplete until
        Phase 2 finishes.
        """
        self._add_properties_by_class(limit=4)
        self.show_child()

        # Connect once per PropertyFrame lifetime (pool reuse / repeated _finish_init).
        if not self._show_child_signal_connected:
            self.ui.show_child.clicked.connect(self.show_child)
            self._show_child_signal_connected = True

        self.init_ui()

        # Defer Phase 2 — lets Qt process one paint event first
        QTimer.singleShot(30, self._finish_init_phase2)

    def _finish_init_phase2(self):
        """
        Phase 2: populate remaining properties and finalize the value dict.
        _setup_layout2dgrid_suppression requires ALL widgets to be present.
        on_edited() is called here for the first time — value dict is now complete.
        """
        self._add_properties_by_class(offset=4)
        self._setup_layout2dgrid_suppression()
        self.on_edited()
    @exception_handler
    def _add_properties_by_class(self, limit=None, offset=0):
        # This function adds property widgets when needed
        def adding_instances(value_class, val):
            def add_instance():
                property_instance.edited.connect(self.on_edited)
                property_instance.setAcceptDrops(False)
                self.ui.layout.insertWidget(0, property_instance)
                if hasattr(property_instance, 'slider_pressed'):
                    property_instance.slider_pressed.connect(self.slider_pressed)
                if hasattr(property_instance, 'committed'):
                    property_instance.committed.connect(self.committed)

            # ---- FAST PATH: skip list ----
            if value_class in PropertyFrame._SKIP_PROPS:
                return

            # ---- FAST PATH: exact dispatch ----
            PropertyFrame._resolve_dispatch()
            dispatch = PropertyFrame._EXACT_PROP_DISPATCH
            if dispatch is not None and value_class in dispatch:
                widget_cls, extra_kwargs = dispatch[value_class]

                # PropertyReference needs tree hierarchy to enable its "search" popup.
                if widget_cls is PropertyReference:
                    property_instance = widget_cls(
                        value=val,
                        value_class=value_class,
                        variables_scrollArea=self.variables_scrollArea,
                        element_id_generator=self.element_id_generator,
                        tree_hierarchy=self.tree_hierarchy,
                        **extra_kwargs
                    )
                else:
                    # Prefer pooling if the widget supports it.
                    if hasattr(widget_cls, "acquire") and callable(getattr(widget_cls, "acquire")):
                        property_instance = widget_cls.acquire(
                            value=val,
                            value_class=value_class,
                            variables_scrollArea=self.variables_scrollArea,
                            element_id_generator=self.element_id_generator,
                            **extra_kwargs,
                        )
                    else:
                        property_instance = widget_cls(
                            value=val,
                            value_class=value_class,
                            variables_scrollArea=self.variables_scrollArea,
                            element_id_generator=self.element_id_generator,
                            **extra_kwargs
                        )

                add_instance()
                return

            if value_class == 'm_bEnabled':
                property_instance = PropertyBool.acquire(
                    value=val,
                    value_class=value_class,
                    variables_scrollArea=self.variables_scrollArea,
                    element_id_generator=self.element_id_generator,
                )
                add_instance()
            elif 'm_nPickMode' in value_class:
                property_instance = PropertyCombobox.acquire(value=val, value_class=value_class,variables_scrollArea=self.variables_scrollArea,items=['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'],filter_types=['PickMode'],element_id_generator=self.element_id_generator);
                add_instance()
            elif value_class == 'm_sLabel':
                pass
            elif value_class == 'm_nElementID':
                pass
            elif value_class == 'm_nReferenceID':
                property_instance = PropertyReference(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator, tree_hierarchy=self.tree_hierarchy)
                add_instance()
            elif value_class == 'm_sReferenceObjectID':
                pass
            elif 'm_nScaleMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NONE','SCALE_END_TO_FIT','SCALE_EQUALLY','SCALE_MAXIMAIZE'], filter_types=['ScaleMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_CoordinateSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_DirectionSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['DirectionSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_GridPlacementMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SEGMENT','FILL'], filter_types=['GridPlacementMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_GridArrangement' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SEGMENT','FILL'], filter_types=['GridPlacementMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_GridOriginMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['CENTER','CORNER'], filter_types=['GridOriginMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_nNoHitResult' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NOTHING','DISCARD','MOVE_TO_START','MOVE_TO_END'], filter_types=['TraceNoHit'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_SelectionMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM','FIRST','SPECIFIC'], filter_types=['ChoiceSelectionMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_PlacementMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SPHERE','CIRCLE','RING'], filter_types=['RadiusPlacementMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_DistributionMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['RANDOM','UNIFORM'], filter_types=['DistributionMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_SpacingSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_sPhysicsType' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['normal','multiplayer'], filter_types=['String'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_DetailObjectFadeLevel' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['NEAR','MEDIUM','FAR','ALWAYS'], filter_types=['String'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_RotationAxes' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['X','Y','Z','XY','XZ','YZ','XYZ'], filter_types=['Axes'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_HandleShape' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['SQUARE','DIAMOND','CIRCLE'], filter_types=['HandleShape'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_nDeformableAttachmentMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['DEFAULT','ATTACH'], filter_types=['SmartPropDeformableAttachMode_t'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_nDeformableOrientationMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['DEFAULT','FOLLOW','IGNORE'], filter_types=['SmartPropDeformableOrientMode_t'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_PointSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_PathSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_UpDirectionSpace' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ELEMENT','OBJECT','WORLD'], filter_types=['CoordinateSpace'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_PlaceAtPositions' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['ALL','NTH','START_AND_END','CONTROL_POINTS'], filter_types=['PathPositions'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_Mode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT','MULTIPLY_CURRENT','REPLACE'], filter_types=['ApplyColorMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_ApplyColorMode' in value_class: property_instance = PropertyCombobox.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, items=['MULTIPLY_OBJECT','MULTIPLY_CURRENT','REPLACE'], filter_types=['ApplyColorMode'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_v' in value_class: property_instance = PropertyVector3D.acquire(
                value=val,
                value_class=value_class,
                variables_scrollArea=self.variables_scrollArea,
                element_id_generator=self.element_id_generator,
            ); add_instance()
            elif 'm_flBendPoint' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, slider_range=[0,1], element_id_generator=self.element_id_generator); add_instance()
            elif value_class in ('m_flWidth','m_flLength','m_flSpacingWidth','m_flSpacingLength','m_flAlternateShiftWidth','m_flAlternateShiftLength'): property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, slider_range=[0,4096], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_fl' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_f' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_HandleSize' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif value_class in ('m_nCountW','m_nCountL'): property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True, slider_range=[0,256], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_n' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_SpecificChildIndex' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_ColorSelection' in value_class: property_instance = PropertyFloat.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, int_bool=True, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_HandleColor' in value_class: property_instance = PropertyColor.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_ColorChoices' in value_class: property_instance = PropertyColorMatch(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_MaterialReplacements' in value_class: property_instance = PropertyMaterialReplacements(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_b' in value_class: property_instance = PropertyBool.acquire(
                value=val,
                value_class=value_class,
                variables_scrollArea=self.variables_scrollArea,
                element_id_generator=self.element_id_generator,
            ); add_instance()
            elif 'm_s' in value_class: property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='String', element_id_generator=self.element_id_generator); add_instance()
            elif 'm_MaterialGroupName' in value_class: property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, placeholder='Material group name', element_id_generator=self.element_id_generator); add_instance()
            elif 'm_Expression' in value_class: property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=True, placeholder='Expression example: var_bool ? var_sizer * var_multiply', element_id_generator=self.element_id_generator); add_instance()
            elif 'm_StateName' in value_class: property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=True, placeholder='State name', element_id_generator=self.element_id_generator); add_instance()
            elif value_class in self.only_variable_properties: property_instance = PropertyVariableOutput(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_VariableName' in value_class: property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=False, only_string=False, only_variable=True, force_variable=True, placeholder='Variable name', filter_types=['String','Int','Float','Bool'], element_id_generator=self.element_id_generator); add_instance()
            elif 'm_Comment' in value_class: property_instance = PropertyComment(value=val, value_class=value_class); add_instance()
            elif 'm_VariableValue' in value_class:
                if val is None:
                    property_instance = PropertyVariableValue(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
                else:
                    if 'm_TargetName' not in val:
                        property_instance = PropertyString.acquire(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, expression_bool=True, element_id_generator=self.element_id_generator); add_instance()
                    else:
                        property_instance = PropertyVariableValue(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); add_instance()
            elif 'm_VariableComparison' in value_class: property_instance = PropertyComparison(value=val, value_class=value_class, variables_scrollArea=self.variables_scrollArea, element_id_generator=self.element_id_generator); self.ui.property_class.setText('Variable Comparison'); add_instance()
            elif 'm_AllowedSurfaceProperties' in value_class: property_instance = PropertySurface(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()
            elif 'm_DisallowedSurfaceProperties' in value_class: property_instance = PropertySurface(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()
            else: property_instance = PropertyLegacy(value=val,value_class=value_class,variables_scrollArea=self.variables_scrollArea); add_instance()

        parent_widget = self.ui.layout.parentWidget()
        try:
            if parent_widget is not None:
                parent_widget.setUpdatesEnabled(False)

            # Prefer worker-prepared ordered pairs (Plan 5).
            if getattr(self, '_ordered_pairs', None) is not None:
                ordered_pairs = self._ordered_pairs
            elif self.prop_class in self._prop_classes_map_cache:
                classes = self._prop_classes_map_cache[self.prop_class]
                ordered_pairs = [
                    (item, self.value.get(item, None))
                    for item in reversed(classes)
                ]
            else:
                ordered_pairs = list(reversed(list(self.value.items())))

            end = (offset + limit) if limit is not None else None
            sliced = ordered_pairs[offset:end]
            for value_class, val_data in sliced:
                adding_instances(value_class, val_data)
        finally:
            if parent_widget is not None:
                parent_widget.setUpdatesEnabled(True)
                parent_widget.update()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_edited(self):

        self.value = {
            '_class': f'{self.name_prefix}_{self.name}',
            'm_nElementID': self.element_id,
        }

        try:
            for index in range(self.ui.layout.count()):
                widget = self.ui.layout.itemAt(index).widget()
                new_value = getattr(widget, 'value', None)
                if new_value:
                    self.value.update(new_value)
        except Exception as error:
            pass

        self.edited.emit()

    def update_self(self):
        pass

    def _clear_widgets(self):
        """
        Remove and schedule destruction of all property child widgets.
        Calls setParent(None) before deleteLater() to immediately detach from
        the layout — prevents a double-widget race if the frame is reused
        before the event loop processes deleteLater().
        """
        while self.ui.layout.count():
            item = self.ui.layout.takeAt(0)
            w = item.widget()
            if w is not None:
                try:
                    # Pooled widgets should be returned to their pool.
                    if hasattr(type(w), "release") and callable(getattr(type(w), "release")):
                        type(w).release(w)
                    else:
                        w.setParent(None)
                        w.deleteLater()
                except Exception:
                    # If pooling fails for any reason, fall back to safe deletion.
                    w.setParent(None)
                    w.deleteLater()

    def _reconfigure(
        self,
        value,
        variables_scrollArea,
        element_id_generator,
        widget_list,
        tree_hierarchy,
        precomputed=None,
    ):
        """
        Reconfigure this pooled PropertyFrame with new data.
        Called by PropertyWidgetPool.acquire().
        """
        import ast as _ast

        self.cancel_worker()
        # Invalidate any in-flight worker results (race safety).
        self._worker_generation = getattr(self, "_worker_generation", 0) + 1
        self._ordered_pairs = None

        self._clear_widgets()

        self.variables_scrollArea = variables_scrollArea
        self.widget_list = widget_list
        self.tree_hierarchy = tree_hierarchy
        self.element_id_generator = element_id_generator

        if self._is_complete_precomputed_payload(precomputed):
            self._apply_precomputed_payload(precomputed)
            self.show()
            QTimer.singleShot(0, self._finish_init)
            return

        if not isinstance(value, dict):
            value = _ast.literal_eval(value)

        if "_class" not in value:
            raise ValueError("PropertyFrame._reconfigure: value dict missing '_class'")

        self.name_prefix, self.name = value["_class"].split("_", 1)
        value = dict(value)
        del value["_class"]

        # Definition of the value variable before getting property data.
        self.value = {"m_bEnabled": True}
        self.value.update(value)

        self.element_id_generator.update_value(self.value)
        self.element_id = self.element_id_generator.get_key(self.value)

        self.ui.element_id_display.setText(str(self.element_id))
        self.prop_class = self.name
        self.ui.property_class.setText(self.name)

        self.show()
        QTimer.singleShot(0, self._finish_init)

    def cancel_worker(self):
        """Cancel in-flight PropertyDataWorker (thread-safe); clears active reference."""
        w = getattr(self, "_active_worker", None)
        if w is not None:
            try:
                w.cancel()
            except Exception:
                pass
            self._active_worker = None

    def _start_data_worker(self):
        """Dispatch data preparation to QThreadPool worker."""
        if not hasattr(self, "_worker_raw_value_with_class"):
            # No raw payload available — fall back to synchronous init.
            self._ordered_pairs = None
            self._finish_init()
            return

        self.cancel_worker()
        self._worker_generation += 1
        expected_gen = self._worker_generation

        worker = PropertyDataWorker(
            raw_value=self._worker_raw_value_with_class,
            element_id_generator=self.element_id_generator,
            prop_classes_map_cache=self._prop_classes_map_cache,
            only_variable_properties=self.only_variable_properties,
            ordered_pairs_cache=self._ORDERED_PAIRS_CACHE,
        )

        # Store signals reference to prevent premature GC.
        self._worker_signals = worker.signals
        self._active_worker = worker

        def _on_ready(prepared_data, gen=expected_gen):
            self._on_data_ready(prepared_data, gen)

        def _on_error(error_msg, gen=expected_gen):
            self._on_data_error(error_msg, gen)

        worker.signals.finished.connect(_on_ready)
        worker.signals.error.connect(_on_error)
        self._get_worker_pool().start(worker)

    def _on_data_ready(self, prepared_data: dict, expected_gen: int):
        """
        Called on main thread when worker finishes.
        Guards against:
          1) the frame being destroyed
          2) staleness (frame reused after a new worker started)
        """
        if expected_gen != getattr(self, "_worker_generation", None):
            return

        try:
            _ = self.ui.layout
        except RuntimeError:
            return

        self._active_worker = None

        self.value = prepared_data["value"]
        self.name_prefix = prepared_data["name_prefix"]
        self.name = prepared_data["name"]
        self.element_id = prepared_data["element_id"]
        self.prop_class = prepared_data["prop_class"]
        self._ordered_pairs = prepared_data["ordered_pairs"]

        self.ui.element_id_display.setText(str(self.element_id))
        self.ui.property_class.setText(self.name)

        self._finish_init()

    def _on_data_error(self, error_msg: str, expected_gen: int):
        """Fallback when worker fails: build ordered pairs synchronously."""
        if expected_gen != getattr(self, "_worker_generation", None):
            return

        self._active_worker = None

        debug(f"PropertyDataWorker error — falling back to sync init: {error_msg}")
        self._ordered_pairs = None
        self._finish_init()

    def _setup_layout2dgrid_suppression(self):
        # Apply visibility rules for Layout2DGrid element
        if getattr(self, 'prop_class', None) != 'Layout2DGrid':
            return

        # Helper to find widgets by value_class
        def find_widget(value_class_name):
            for i in range(self.ui.layout.count()):
                w = self.ui.layout.itemAt(i).widget()
                if w is not None and hasattr(w, 'value_class') and w.value_class == value_class_name:
                    return w
            return None

        # Cache relevant widgets
        self._w_arrangement = find_widget('m_GridArrangement') or find_widget('m_GridPlacementMode')
        self._w_count_w = find_widget('m_nCountW')
        self._w_count_l = find_widget('m_nCountL')
        self._w_spacing_w = find_widget('m_flSpacingWidth') or find_widget('m_flSpacingW')
        self._w_spacing_l = find_widget('m_flSpacingLength') or find_widget('m_flSpacingL')
        self._w_alt = find_widget('m_bAlternateShift')
        self._w_shift_w = find_widget('m_flAlternateShiftWidth')
        self._w_shift_l = find_widget('m_flAlternateShiftLength')

        # Connect signals
        if self._w_arrangement and hasattr(self._w_arrangement, 'edited'):
            self._w_arrangement.edited.connect(self._update_layout2dgrid_visibility)
        if self._w_alt and hasattr(self._w_alt, 'edited'):
            self._w_alt.edited.connect(self._update_layout2dgrid_visibility)

        # Initial apply
        self._update_layout2dgrid_visibility()

    def _update_layout2dgrid_visibility(self):
        if getattr(self, 'prop_class', None) != 'Layout2DGrid':
            return

        # Read arrangement mode as string when possible
        mode = None
        if getattr(self, '_w_arrangement', None) is not None:
            val = getattr(self._w_arrangement, 'value', None)
            if isinstance(val, dict):
                v = val.get('m_GridArrangement') or val.get('m_GridPlacementMode')
                if isinstance(v, str):
                    mode = v

        # Read alternate shift as bool when possible
        alt = False
        if getattr(self, '_w_alt', None) is not None:
            val = getattr(self._w_alt, 'value', None)
            if isinstance(val, dict):
                v = val.get('m_bAlternateShift')
                if isinstance(v, bool):
                    alt = v

        # Default: if mode unknown, show everything to avoid hiding usable fields
        show_all = mode not in ('SEGMENT', 'FILL')

        widgets = [
            ('segment', [self._w_count_w, self._w_count_l, self._w_alt]),
            ('shift', [self._w_shift_w, self._w_shift_l]),
            ('fill', [self._w_spacing_w, self._w_spacing_l])
        ]

        # Helper for visibility
        def set_list_visible(lst, visible):
            for w in lst:
                if w is not None:
                    w.setVisible(visible)

        if show_all:
            # Show everything if we cannot evaluate mode
            for _, lst in widgets:
                set_list_visible(lst, True)
            return

        if mode == 'SEGMENT':
            set_list_visible([self._w_count_w, self._w_count_l, self._w_alt], True)
            set_list_visible([self._w_spacing_w, self._w_spacing_l], False)
            # Shift fields depend on alt
            set_list_visible([self._w_shift_w, self._w_shift_l], bool(alt))
        elif mode == 'FILL':
            set_list_visible([self._w_spacing_w, self._w_spacing_l], True)
            set_list_visible([self._w_count_w, self._w_count_l, self._w_alt, self._w_shift_w, self._w_shift_l], False)

    def init_ui(self):
        if self.element:
            pass
        else:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            if not self._context_menu_signal_connected:
                self.customContextMenuRequested.connect(self.show_context_menu)
                self._context_menu_signal_connected = True

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
                if source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)
        self.edited.emit()
        event.accept()

    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)
        context_menu.addActions([delete_action, copy_action])
        action = context_menu.exec(QCursor.pos())
        if action == delete_action:
            self.delete_action()
        elif action == copy_action:
            self.copy_action()

    def copy_action(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(f"hammer5tools:smartprop_editor_property;;{self.name};;{self.value}")

    def delete_action(self):
        self.value = None
        self.edited.emit()
        self.cancel_worker()
        # Invalidate any in-flight worker results (race safety).
        self._worker_generation = getattr(self, "_worker_generation", 0) + 1
        self._ordered_pairs = None

        # Deferred import to avoid circular import at module load time.
        try:
            from src.editors.smartprop_editor.property_widget_pool import PropertyWidgetPool
            PropertyWidgetPool.instance().release(self.prop_class, self)
        except Exception:
            self.deleteLater()


PropertyFrame._build_ordered_pairs_cache()