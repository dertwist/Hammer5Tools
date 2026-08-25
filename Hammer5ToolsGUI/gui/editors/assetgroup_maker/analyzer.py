import os
import re
from typing import Dict, List, Optional, Tuple
from gui.settings.main import get_addon_dir, debug


class ReferenceAnalysisResult:
    """Stores the parsed structure of a reference template file."""

    def __init__(self, reference_path: str):
        self.reference_path = reference_path
        self.asset_type = self._detect_type(reference_path)
        self.base_name = os.path.splitext(os.path.basename(reference_path))[0]
        self.slots: Dict[str, Dict] = {}
        self.material_remaps: List[Dict[str, str]] = []
        self.replacements: Dict[str, Dict] = {}
        self.raw_content: str = ""
        self.template_content: str = ""

    @staticmethod
    def _detect_type(path: str) -> str:
        ext = os.path.splitext(path)[1].lower().strip('.')
        if ext in ('vmdl', 'vmat', 'vsmart', 'vsndevts'):
            return ext
        return 'vmdl'


def extract_fbx_materials(file_path: str) -> List[str]:
    """
    Extract embedded material names from an FBX file (binary or ASCII).
    Uses UnrealPorter's fbx_flatten.list_materials with ASCII token fallback.
    """
    if not file_path or not os.path.isfile(file_path):
        return []
    try:
        from gui.forms.unreal_porter.fbx_flatten import list_materials
        mats = list_materials(file_path)
        if mats:
            return mats
    except Exception:
        pass

    # Fallback for ASCII FBX or non-standard headers
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        text = data.decode('latin-1', errors='ignore')
        matches = re.findall(r'Material:\s*[^,]+,\s*["\'](?:Material::)?([^"\']+)["\']', text)
        if not matches:
            matches = re.findall(r'Material::([a-zA-Z0-9_\-]+)', text)
        seen = set()
        res = []
        for m in matches:
            clean = m.split('\x00')[0].split('\x01')[0].strip()
            if clean and clean not in seen and clean.lower() not in ('defaultmaterial', 'material'):
                seen.add(clean)
                res.append(clean)
        return res
    except Exception:
        return []


def get_addon_root_from_path(file_path: str) -> Optional[str]:
    """Extracts the addon root directory from an absolute file path containing csgo_addons."""
    if not file_path:
        return None
    normalized = file_path.replace('\\', '/')
    match = re.search(r'^(.*?/content/csgo_addons/[^/]+)', normalized, re.IGNORECASE)
    if match:
        return os.path.normpath(match.group(1))
    return None


def resolve_reference_full_path(reference_path: str, context_folder: Optional[str] = None) -> Optional[str]:
    """Resolves the full path to a reference file across context folders and addon directories."""
    if not reference_path:
        return None
    if os.path.isabs(reference_path) and os.path.isfile(reference_path):
        return os.path.normpath(reference_path)

    candidates = []

    # 1. From context folder
    if context_folder:
        addon_root = get_addon_root_from_path(context_folder)
        if addon_root:
            candidates.append(os.path.join(addon_root, reference_path))
        candidates.append(os.path.join(context_folder, reference_path))
        candidates.append(os.path.join(context_folder, os.path.basename(reference_path)))

    # 2. From global settings addon dir
    addon_dir = get_addon_dir()
    if addon_dir:
        candidates.append(os.path.join(addon_dir, reference_path))

    # 3. Direct relative to cwd
    candidates.append(os.path.abspath(reference_path))

    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)

    return None


def analyze_reference_file(reference_rel_path: str, context_folder: Optional[str] = None) -> ReferenceAnalysisResult:
    """
    Analyzes a reference file (relative to addon directory, context folder, or absolute)
    and extracts its referenced source files, slots, and token replacements.
    """
    full_path = resolve_reference_full_path(reference_rel_path, context_folder=context_folder)
    if not full_path:
        addon_dir = get_addon_dir()
        if os.path.isabs(reference_rel_path):
            full_path = os.path.normpath(reference_rel_path)
        else:
            full_path = os.path.join(addon_dir, reference_rel_path) if addon_dir else reference_rel_path

    result = ReferenceAnalysisResult(reference_rel_path)

    if not full_path or not os.path.isfile(full_path):
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
        _analyze_vmdl(result, content, context_folder=context_folder)
    elif result.asset_type == 'vmat':
        _analyze_vmat(result, content)
    elif result.asset_type == 'vsmart':
        _analyze_vsmart(result, content)
    else:
        _analyze_generic(result, content)

    return result


def _analyze_vmdl(result: ReferenceAnalysisResult, content: str, context_folder: Optional[str] = None):
    """Analyze a Source 2 ModelDoc .vmdl file."""
    base = result.base_name

    # 1. Look for explicit physics mesh blocks first
    phys_blocks = re.findall(r'(?:PhysicsHullFile|PhysicsMeshFile)[\s\S]*?filename\s*=\s*["\']([^"\']+\.(?:fbx|obj|dmx))["\']', content, re.IGNORECASE)
    render_blocks = re.findall(r'RenderMeshFile[\s\S]*?filename\s*=\s*["\']([^"\']+\.(?:fbx|obj|dmx))["\']', content, re.IGNORECASE)

    collision_mesh = phys_blocks[0] if phys_blocks else None
    primary_mesh = render_blocks[0] if render_blocks else None
    lod_meshes = []
    extra_meshes = []

    # 2. General scan if explicit blocks didn't catch both
    all_mesh_matches = re.findall(r'filename\s*=\s*["\']([^"\']+\.(?:fbx|obj|dmx))["\']', content, re.IGNORECASE)
    for mesh_path in all_mesh_matches:
        mesh_filename = os.path.basename(mesh_path)
        mesh_base, _ = os.path.splitext(mesh_filename)
        b_lower = mesh_base.lower()

        # Check if it's collision
        if b_lower.startswith(('phys_', 'col_', 'hull_', 'physics_', 'collision_')) or any(
            s in b_lower for s in ('_phys', '_col', '_hull', '_collision', '_physics')
        ):
            if not collision_mesh:
                collision_mesh = mesh_path
        # Check if it's LOD
        elif b_lower.startswith(('lod1_', 'lod2_')) or re.search(r'_lod[1-9]', b_lower):
            if mesh_path not in lod_meshes:
                lod_meshes.append(mesh_path)
        else:
            if not primary_mesh:
                primary_mesh = mesh_path
            elif mesh_path not in extra_meshes and mesh_path != primary_mesh:
                extra_meshes.append(mesh_path)

    # Fallback if primary wasn't found but meshes exist
    if not primary_mesh and all_mesh_matches:
        primary_mesh = all_mesh_matches[0]

    # Populate slots
    if primary_mesh:
        result.slots['mesh'] = {
            'label': 'Render Mesh (LOD0)',
            'source': primary_mesh,
            'filename': os.path.basename(primary_mesh),
            'required': True,
            'token': '#$MESH$#'
        }

    for idx, extra_path in enumerate(extra_meshes, start=1):
        slot_key = f'mesh_{idx}'
        result.slots[slot_key] = {
            'label': f'Extra Mesh {idx}',
            'source': extra_path,
            'filename': os.path.basename(extra_path),
            'required': False,
            'token': f'#$MESH_{idx}$#'
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

    # 3. Extract MaterialGroup remaps: { from = "mi_bark.vmat", to = "materials/.../bark.vmat" }
    remap_matches = re.findall(r'{\s*from\s*=\s*["\']([^"\']+)["\']\s*to\s*=\s*["\']([^"\']+)["\']\s*}', content, re.IGNORECASE)
    seen_from = set()
    for from_mat, to_mat in remap_matches:
        f_clean = from_mat.strip()
        if f_clean and f_clean.lower() not in seen_from:
            seen_from.add(f_clean.lower())
            result.material_remaps.append({'from': f_clean, 'to': to_mat.strip()})

    # 4. Research FBX materials from referenced render mesh(es)
    all_render_meshes = [primary_mesh] + extra_meshes + lod_meshes
    for r_mesh in all_render_meshes:
        if not r_mesh:
            continue
        mesh_full = resolve_reference_full_path(r_mesh, context_folder=context_folder)
        if mesh_full and mesh_full.lower().endswith('.fbx') and os.path.isfile(mesh_full):
            fbx_mats = extract_fbx_materials(mesh_full)
            for f_mat in fbx_mats:
                f_vmat = f_mat if f_mat.lower().endswith('.vmat') else f"{f_mat}.vmat"
                if f_vmat.lower() not in seen_from and f_mat.lower() not in seen_from:
                    seen_from.add(f_vmat.lower())
                    result.material_remaps.append({'from': f_vmat, 'to': ""})

    # 5. Single material reference fallback (e.g. global_default_material = "...crate_01.vmat")
    mat_matches = re.findall(r'(?:global_default_material|m_sMaterialName)\s*=\s*["\']([^"\']+\.vmat)["\']', content, re.IGNORECASE)
    for mat_path in mat_matches:
        mat_filename = os.path.basename(mat_path)
        mat_base, _ = os.path.splitext(mat_filename)
        if not result.material_remaps and (base.lower() in mat_base.lower() or mat_path):
            result.material_remaps.append({'from': mat_filename, 'to': mat_path})
            break

    # Populate material remap slots in result.slots
    for idx, remap in enumerate(result.material_remaps):
        slot_key = f'material_{idx}' if idx > 0 else 'material'
        from_mat = remap.get('from', '')
        to_mat = remap.get('to', '')
        result.slots[slot_key] = {
            'label': f'Material: {from_mat}',
            'from': from_mat,
            'to': to_mat,
            'source': to_mat,
            'filename': os.path.basename(to_mat) if to_mat else '',
            'is_material_remap': True,
            'required': False,
            'token': f'#${slot_key.upper()}$#'
        }

    _build_replacements_and_template(result)


def _analyze_vmat(result: ReferenceAnalysisResult, content: str):
    """Analyze a Source 2 Material .vmat file."""
    base = result.base_name

    # Comprehensive CS2 shader texture map patterns with clean names
    tex_patterns = [
        # Layer 1 / Primary Slots
        ('color', 'Color Map', r'([ \t]*(?:g_tColor|TextureColor|TextureDiffuse|g_tBaseColor|g_tAlbedo|g_tColorA)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('normal', 'Normal Map', r'([ \t]*(?:g_tNormal|TextureNormal|g_tNormalRoughness|g_tNormalA)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('roughness', 'Roughness Map', r'([ \t]*(?:g_tRoughness|TextureRoughness)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('metalness', 'Metalness Map', r'([ \t]*(?:g_tMetalness|TextureMetalness)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('ao', 'Ambient Occlusion Map', r'([ \t]*(?:g_tAmbientOcclusion|TextureAmbientOcclusion|g_tAO)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('orm', 'ORM Map', r'([ \t]*(?:g_tORM|g_tMask|g_tMasks|g_tRMA|g_tSRM|g_tSRMH|TextureORM|TextureMask)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('height', 'Height Map', r'([ \t]*(?:g_tHeight|TextureHeight|g_tDisplacement|TextureDisplacement)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('emissive', 'Emissive Map', r'([ \t]*(?:g_tSelfIllumMask|TextureSelfIllumMask|g_tEmissiveMask|g_tEmission|g_tSelfIllum|TextureSelfIllum)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('opacity', 'Opacity Map', r'([ \t]*(?:g_tTranslucency|TextureTranslucency|g_tOpacityMask|TextureOpacityMask|g_tAlpha|g_tTranslucencyMask)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('tintmask', 'Tint Mask', r'([ \t]*(?:g_tTintMask|TextureTintMask)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('transmission', 'Transmission Map', r'([ \t]*(?:g_tTransmissionMask|g_tSubsurfaceColor)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('blendmask', 'Layer Blend Mask', r'([ \t]*(?:g_tBlendMask|g_tLayerBlendMask)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),

        # Layer 2 Blend Slots
        ('color2', 'Layer 2 Color Map', r'([ \t]*(?:g_tColorB|g_tLayer2Color|TextureColor2)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('normal2', 'Layer 2 Normal Map', r'([ \t]*(?:g_tNormalB|g_tLayer2Normal|TextureNormal2)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('roughness2', 'Layer 2 Roughness Map', r'([ \t]*(?:g_tLayer2Roughness|TextureRoughness2)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('metalness2', 'Layer 2 Metalness Map', r'([ \t]*(?:g_tLayer2Metalness|TextureMetalness2)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('ao2', 'Layer 2 Ambient Occlusion Map', r'([ \t]*(?:g_tLayer2AmbientOcclusion|TextureAmbientOcclusion2)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('orm2', 'Layer 2 ORM Map', r'([ \t]*(?:g_tLayer2ORM|TextureLayer2ORM)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),

        # Layer 3 Blend Slots
        ('color3', 'Layer 3 Color Map', r'([ \t]*(?:g_tColorC|g_tLayer3Color|TextureColor3)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
        ('normal3', 'Layer 3 Normal Map', r'([ \t]*(?:g_tNormalC|g_tLayer3Normal|TextureNormal3)[0-9A-Za-z_]*\s*=?\s*(?:resource:)?["\']([^"\']+\.(?:png|tga|jpg|jpeg|exr|hdr|psd|tif|tiff))["\'])'),
    ]

    for slot_key, label, pattern in tex_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            full_match_line = match.group(1)
            tex_path = match.group(2)
            result.slots[slot_key] = {
                'label': label,
                'source': tex_path,
                'full_line': full_match_line,
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
    into a reusable template string with slot conditionals.
    """
    content = result.raw_content
    base = result.base_name
    replacements_dict = {}
    rep_idx = 0

    # 1. Replace specific slot files first, longest string first to avoid substring conflicts
    sorted_slots = sorted(
        result.slots.items(),
        key=lambda item: len(item[1].get('source', '') or item[1].get('filename', '')),
        reverse=True
    )
    for slot_name, slot_info in sorted_slots:
        source_path = slot_info.get('source', '')
        source_filename = slot_info.get('filename', '')
        full_line = slot_info.get('full_line', '')

        if full_line and full_line in content:
            # Replace source_path within full_line and wrap in conditional
            param_line = full_line.replace(source_path, f"#$FOLDER_PATH$#/#${slot_name.upper()}$#")
            cond_block = f"<!-- IF {slot_name.upper()} -->\n{param_line}\n<!-- ENDIF -->"
            content = content.replace(full_line, cond_block)
            replacements_dict[str(rep_idx)] = {
                'replacement': [source_path, f"#$FOLDER_PATH$#/#${slot_name.upper()}$#"]
            }
            rep_idx += 1
        elif source_path and source_path in content:
            content = content.replace(source_path, f"#$FOLDER_PATH$#/#${slot_name.upper()}$#")
            replacements_dict[str(rep_idx)] = {
                'replacement': [source_path, f"#$FOLDER_PATH$#/#${slot_name.upper()}$#"]
            }
            rep_idx += 1
        elif source_filename and source_filename in content:
            content = content.replace(source_filename, f"#${slot_name.upper()}$#")
            replacements_dict[str(rep_idx)] = {
                'replacement': [source_filename, f"#${slot_name.upper()}$#"]
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
