import os
import re
from typing import Dict, List, Optional, Tuple
from src.settings.main import get_addon_dir, debug


class ReferenceAnalysisResult:
    """Stores the parsed structure of a reference template file."""

    def __init__(self, reference_path: str):
        self.reference_path = reference_path
        self.asset_type = self._detect_type(reference_path)
        self.base_name = os.path.splitext(os.path.basename(reference_path))[0]
        self.slots: Dict[str, Dict] = {}
        self.replacements: Dict[str, Dict] = {}
        self.raw_content: str = ""
        self.template_content: str = ""

    @staticmethod
    def _detect_type(path: str) -> str:
        ext = os.path.splitext(path)[1].lower().strip('.')
        if ext in ('vmdl', 'vmat', 'vsmart', 'vsndevts'):
            return ext
        return 'vmdl'


def analyze_reference_file(reference_rel_path: str) -> ReferenceAnalysisResult:
    """
    Analyzes a reference file (relative to addon directory or absolute)
    and extracts its referenced source files, slots, and token replacements.
    """
    addon_dir = get_addon_dir()
    if os.path.isabs(reference_rel_path):
        full_path = os.path.normpath(reference_rel_path)
        if addon_dir:
            try:
                reference_rel_path = os.path.relpath(full_path, addon_dir)
            except ValueError:
                pass
    else:
        full_path = os.path.join(addon_dir, reference_rel_path) if addon_dir else reference_rel_path

    result = ReferenceAnalysisResult(reference_rel_path)

    if not os.path.isfile(full_path):
        debug(f"[Analyzer] Reference file does not exist: {full_path}")
        return result

    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        debug(f"[Analyzer] Failed to read reference file: {e}")
        return result

    result.raw_content = content
    result.template_content = content

    if result.asset_type == 'vmdl':
        _analyze_vmdl(result, content)
    elif result.asset_type == 'vmat':
        _analyze_vmat(result, content)
    elif result.asset_type == 'vsmart':
        _analyze_vsmart(result, content)
    else:
        _analyze_generic(result, content)

    return result


def _analyze_vmdl(result: ReferenceAnalysisResult, content: str):
    """Analyze a Source 2 ModelDoc .vmdl file."""
    base = result.base_name

    # 1. Look for render mesh files (e.g. filename = "models/props/.../crate_01.fbx")
    mesh_matches = re.findall(r'filename\s*=\s*["\']([^"\']+\.(?:fbx|obj|dmx))["\']', content, re.IGNORECASE)
    
    primary_mesh = None
    collision_mesh = None
    lod_meshes = []

    for mesh_path in mesh_matches:
        mesh_filename = os.path.basename(mesh_path)
        mesh_base, _ = os.path.splitext(mesh_filename)

        # Check if it's collision
        if any(s in mesh_base.lower() for s in ('_phys', '_col', '_hull', '_collision')):
            collision_mesh = mesh_path
        # Check if it's LOD
        elif re.search(r'_lod[1-9]', mesh_base, re.IGNORECASE):
            lod_meshes.append(mesh_path)
        else:
            if not primary_mesh:
                primary_mesh = mesh_path

    # Fallback if primary wasn't found but meshes exist
    if not primary_mesh and mesh_matches:
        primary_mesh = mesh_matches[0]

    # Populate slots
    if primary_mesh:
        result.slots['mesh'] = {
            'label': 'Render Mesh (LOD0)',
            'source': primary_mesh,
            'filename': os.path.basename(primary_mesh),
            'required': True,
            'token': '#$MESH$#'
        }

    if collision_mesh:
        result.slots['collision'] = {
            'label': 'Collision Hull',
            'source': collision_mesh,
            'filename': os.path.basename(collision_mesh),
            'required': False,
            'fallback': 'mesh',
            'token': '#$COLLISION$#'
        }

    for idx, lod_path in enumerate(lod_meshes, start=1):
        slot_key = f'lod{idx}'
        result.slots[slot_key] = {
            'label': f'LOD {idx} Mesh',
            'source': lod_path,
            'filename': os.path.basename(lod_path),
            'required': False,
            'token': f'#$LOD{idx}$#'
        }

    # 2. Look for material references (e.g. global_default_material = "...crate_01.vmat")
    mat_matches = re.findall(r'(?:material|global_default_material|m_sMaterialName)\s*=\s*["\']([^"\']+\.vmat)["\']', content, re.IGNORECASE)
    for mat_path in mat_matches:
        mat_filename = os.path.basename(mat_path)
        mat_base, _ = os.path.splitext(mat_filename)
        if base.lower() in mat_base.lower():
            result.slots['material'] = {
                'label': 'Material Remap',
                'source': mat_path,
                'filename': mat_filename,
                'required': False,
                'token': '#$MATERIAL$#'
            }
            break

    _build_replacements_and_template(result)


def _analyze_vmat(result: ReferenceAnalysisResult, content: str):
    """Analyze a Source 2 Material .vmat file."""
    base = result.base_name

    # Look for texture maps: Color, Normal, Roughness, AO, Metalness
    tex_patterns = [
        ('color', 'Albedo / Color Map', r'(?:g_tColor|TextureColor)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
        ('normal', 'Normal Map', r'(?:g_tNormal|TextureNormal)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
        ('roughness', 'Roughness Map', r'(?:g_tRoughness|TextureRoughness)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
        ('ao', 'Ambient Occlusion Map', r'(?:g_tAmbientOcclusion|TextureAmbientOcclusion)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
        ('metalness', 'Metalness Map', r'(?:g_tMetalness|TextureMetalness)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
        ('height', 'Height / Displacement', r'(?:g_tHeight|TextureHeight)\s*=\s*resource:?["\']([^"\']+\.(?:png|tga|jpg|exr|hdr|psd))["\']'),
    ]

    for slot_key, label, pattern in tex_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            tex_path = match.group(1)
            result.slots[slot_key] = {
                'label': label,
                'source': tex_path,
                'filename': os.path.basename(tex_path),
                'required': (slot_key == 'color'),
                'token': f'#${slot_key.upper()}$#'
            }

    _build_replacements_and_template(result)


def _analyze_vsmart(result: ReferenceAnalysisResult, content: str):
    """Analyze a Source 2 SmartProp .vsmart file."""
    base = result.base_name

    # Look for child model references (e.g. m_sModelName = "models/props/.../crate_01.vmdl")
    model_matches = re.findall(r'm_sModelName\s*=\s*["\']([^"\']+\.vmdl)["\']', content, re.IGNORECASE)
    if model_matches:
        for idx, model_path in enumerate(model_matches):
            slot_name = 'model' if idx == 0 else f'model_{idx}'
            result.slots[slot_name] = {
                'label': f'Model {idx+1}' if idx > 0 else 'Primary Model',
                'source': model_path,
                'filename': os.path.basename(model_path),
                'required': (idx == 0),
                'token': f'#$MODEL{f"_{idx}" if idx > 0 else ""}$#'
            }

    _build_replacements_and_template(result)


def _analyze_generic(result: ReferenceAnalysisResult, content: str):
    """Analyze generic KV3 files."""
    _build_replacements_and_template(result)


def _build_replacements_and_template(result: ReferenceAnalysisResult):
    """
    Constructs the replacements mapping and parameterizes the raw content
    into a reusable template string.
    """
    content = result.raw_content
    base = result.base_name
    replacements_dict = {}
    rep_idx = 0

    # 1. Replace specific slot files first
    for slot_name, slot_info in result.slots.items():
        source_path = slot_info.get('source', '')
        source_filename = slot_info.get('filename', '')
        token = slot_info.get('token', f'#${slot_name.upper()}$#')

        if source_filename and source_filename in content:
            content = content.replace(source_filename, token)
            replacements_dict[str(rep_idx)] = {
                'replacement': [source_filename, token]
            }
            rep_idx += 1

    # 2. Replace base asset name occurrences
    if base and base in content:
        content = content.replace(base, '#$ASSET_NAME$#')
        replacements_dict[str(rep_idx)] = {
            'replacement': [base, '#$ASSET_NAME$#']
        }
        rep_idx += 1

    result.replacements = replacements_dict
    result.template_content = content
