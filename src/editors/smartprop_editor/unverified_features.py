"""
SmartProp Editor Verification System Documentation

This module contains the list of SmartProp features (Elements, Filters, Operations)
that are currently NOT fully verified to work properly in the current build of the Source 2 engine (CS2).

How to Add an Unverified Property:
1. Add the '_class' name of the property to the `UNVERIFIED_CLASSES` list below.
2. The UI will automatically insert a "Not Verified in CS2" warning at the top of the property inspector when this class is selected.

How to Mark a Property as Verified:
1. Once a feature is confirmed to be fully functional in the engine, simply remove its '_class' name from the `UNVERIFIED_CLASSES` list below.
2. The warning will automatically disappear from the UI.
"""

UNVERIFIED_CLASSES = (
    'CSmartPropOperation_SetMateraialGroupChoice',
    'CSmartPropOperation_RandomColorTintColor',
    'CSmartPropOperation_SaveColor',
    'CSmartPropOperation_Trace',
    'CSmartPropOperation_SaveSurfaceNormal',
    'CSmartPropOperation_RandomRotationSnapped',
    'CSmartPropOperation_ComputeDotProduct3D',
    'CSmartPropOperation_ComputeCrossProduct3D',
    'CSmartPropOperation_RotateTowards',
    'CSmartPropOperation_TraceToPoint',
    'CSmartPropOperation_TraceToLine',
)
