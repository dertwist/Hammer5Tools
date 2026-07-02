import os
import tempfile
import shutil
import unittest
import re
from src.forms.cleanup.parse import get_mesh_material_references, get_junk_files

class TestCleanupFeature(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure mimicking a Source 2 addon
        self.temp_dir = tempfile.mkdtemp()
        
        # 1. Create subdirectories
        self.maps_dir = os.path.join(self.temp_dir, "maps")
        self.models_dir = os.path.join(self.temp_dir, "models")
        self.materials_dir = os.path.join(self.temp_dir, "materials")
        os.makedirs(self.maps_dir)
        os.makedirs(self.models_dir)
        os.makedirs(self.materials_dir)
        
        # 2. Create a mock FBX file referencing a vmat
        self.fbx_path = os.path.join(self.models_dir, "test_mesh.fbx")
        with open(self.fbx_path, "wb") as f:
            f.write(b"Kaydara FBX Binary  \x00\x1a\x00\x14\x1e\x00\x00")
            f.write(b"some other binary data Material::FBX_vmatPath materials/test_material.vmat more binary data")
            
        # 3. Create a mock DMX file referencing another vmat
        self.dmx_path = os.path.join(self.models_dir, "test_mesh_dmx.dmx")
        with open(self.dmx_path, "wb") as f:
            f.write(b"some binary header \"mtlName\" \"string\" \"materials/test_material_dmx.vmat\" more binary data")
            
        # 4. Create mock vmat files
        self.vmat_path = os.path.join(self.materials_dir, "test_material.vmat")
        with open(self.vmat_path, "w") as f:
            f.write('"Layer0"\n{\n\t"TextureColor"\t"materials/test_texture.png"\n}')
            
        self.vmat_dmx_path = os.path.join(self.materials_dir, "test_material_dmx.vmat")
        with open(self.vmat_dmx_path, "w") as f:
            f.write('"Layer0"\n{\n\t"TextureColor"\t"materials/test_texture_dmx.png"\n}')
            
        self.unused_vmat_path = os.path.join(self.materials_dir, "unused_material.vmat")
        with open(self.unused_vmat_path, "w") as f:
            f.write('"Layer0"\n{\n\t"TextureColor"\t"materials/unused_texture.png"\n}')
            
        # 5. Create mock texture files
        self.tex_path = os.path.join(self.materials_dir, "test_texture.png")
        with open(self.tex_path, "w") as f: f.write("fake png")
        
        self.tex_dmx_path = os.path.join(self.materials_dir, "test_texture_dmx.png")
        with open(self.tex_dmx_path, "w") as f: f.write("fake png dmx")
        
        self.unused_tex_path = os.path.join(self.materials_dir, "unused_texture.png")
        with open(self.unused_tex_path, "w") as f: f.write("fake unused png")
        
        # Create smartprops directory
        self.smartprops_dir = os.path.join(self.temp_dir, "smartprops")
        os.makedirs(self.smartprops_dir)
        
        # Create mock vsmart files
        self.vsmart_path = os.path.join(self.smartprops_dir, "test_prop.vsmart")
        with open(self.vsmart_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{\n\t_class = "CSmartPropElement_Group"\n\tchildren = [\n\t\t{\n\t\t\t_class = "CSmartPropElement_Model"\n\t\t\tm_sModelName = "models/smart_model.vmdl"\n\t\t},\n\t\t{\n\t\t\t_class = "CSmartPropElement_SmartProp"\n\t\t\tm_sSmartProp = "smartprops/nested_prop.vsmart"\n\t\t}\n\t]\n}')
            
        self.nested_vsmart_path = os.path.join(self.smartprops_dir, "nested_prop.vsmart")
        with open(self.nested_vsmart_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{\n\t_class = "CSmartPropElement_Model"\n\tm_sModelName = "models/nested_smart_model.vmdl"\n}')
            
        # Create mock smart models
        self.smart_model_path = os.path.join(self.models_dir, "smart_model.vmdl")
        with open(self.smart_model_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc32:version{c5dcef98-b629-46ab-88e3-a17c005c935e} -->\n{\n\trootNode = {}\n}')
            
        self.nested_smart_model_path = os.path.join(self.models_dir, "nested_smart_model.vmdl")
        with open(self.nested_smart_model_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc32:version{c5dcef98-b629-46ab-88e3-a17c005c935e} -->\n{\n\trootNode = {}\n}')
        
        # 6. Create a mock vmdl file referencing the FBX and DMX
        self.vmdl_path = os.path.join(self.models_dir, "test_model.vmdl")
        with open(self.vmdl_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc32:version{c5dcef98-b629-46ab-88e3-a17c005c935e} -->\n{\n\trootNode = {\n\t\tchildren = [\n\t\t\t{\n\t\t\t\t_class = "RenderMeshFile"\n\t\t\t\tfilename = "/models/test_mesh.fbx"\n\t\t\t},\n\t\t\t{\n\t\t\t\t_class = "RenderMeshFile"\n\t\t\t\tsource_filename = "models/test_mesh_dmx.dmx"\n\t\t\t}\n\t\t]\n\t}\n}')
            
        # 7. Create a mock vmap file referencing the vmdl
        # (We mock the dotnet extract_vmap_references function in the test or write it so it is resolved)
        self.vmap_path = os.path.join(self.maps_dir, "test_map.vmap")
        
        # Mock extract_vmap_references in parse module for this test
        import src.forms.cleanup.parse
        self.original_extract_vmap_references = src.forms.cleanup.parse.extract_vmap_references
        src.forms.cleanup.parse.extract_vmap_references = lambda vmap_path: ["models/test_model.vmdl", "smartprops/test_prop.vsmart"]

    def tearDown(self):
        # Restore original function
        import src.forms.cleanup.parse
        src.forms.cleanup.parse.extract_vmap_references = self.original_extract_vmap_references
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)

    def test_get_mesh_material_references_fbx(self):
        refs = get_mesh_material_references(self.fbx_path)
        self.assertIn("materials/test_material.vmat", refs)

    def test_get_mesh_material_references_dmx(self):
        refs = get_mesh_material_references(self.dmx_path)
        self.assertIn("materials/test_material_dmx.vmat", refs)

    def test_get_smartprop_references(self):
        from src.forms.cleanup.parse import get_vmap_references
        _, referenced_files = get_vmap_references(self.temp_dir, self.vmap_path, scan_meshes=True)
        referenced_lower = set(f.lower() for f in referenced_files)
        self.assertIn("models/smart_model.vmdl", referenced_lower)
        self.assertIn("smartprops/nested_prop.vsmart", referenced_lower)
        self.assertIn("models/nested_smart_model.vmdl", referenced_lower)

    def test_get_junk_files_with_scan_meshes(self):
        # When scan_meshes is True, the referenced vmat and texture files should NOT be junk
        junk = get_junk_files(addon_dir=self.temp_dir, vmap=self.vmap_path, scan_meshes=True)
        junk_paths = [f[0].lower() for f in junk]
        
        # Check that the unused assets ARE marked as junk
        self.assertIn("materials/unused_material.vmat", junk_paths)
        self.assertIn("materials/unused_texture.png", junk_paths)
        
        # Check that the referenced assets ARE NOT marked as junk
        self.assertNotIn("materials/test_material.vmat", junk_paths)
        self.assertNotIn("materials/test_texture.png", junk_paths)
        self.assertNotIn("materials/test_material_dmx.vmat", junk_paths)
        self.assertNotIn("materials/test_texture_dmx.png", junk_paths)
        
        # Smartprop assets should NOT be marked as junk
        self.assertNotIn("models/smart_model.vmdl", junk_paths)
        self.assertNotIn("smartprops/nested_prop.vsmart", junk_paths)
        self.assertNotIn("models/nested_smart_model.vmdl", junk_paths)

    def test_get_junk_files_without_scan_meshes(self):
        # When scan_meshes is False, the assets referenced only inside FBX/DMX SHOULD be marked as junk
        junk = get_junk_files(addon_dir=self.temp_dir, vmap=self.vmap_path, scan_meshes=False)
        junk_paths = [f[0].lower() for f in junk]
        
        # Check that everything is marked as junk (except the models and maps themselves)
        self.assertIn("materials/test_material.vmat", junk_paths)
        self.assertIn("materials/test_texture.png", junk_paths)
        self.assertIn("materials/test_material_dmx.vmat", junk_paths)
        self.assertIn("materials/test_texture_dmx.png", junk_paths)
        self.assertIn("materials/unused_material.vmat", junk_paths)
        self.assertIn("materials/unused_texture.png", junk_paths)
        
        # Smartprop assets should still NOT be marked as junk (since they are referenced from vmap directly/indirectly)
        self.assertNotIn("models/smart_model.vmdl", junk_paths)
        self.assertNotIn("smartprops/nested_prop.vsmart", junk_paths)
        self.assertNotIn("models/nested_smart_model.vmdl", junk_paths)

class TestRealAssetsCleanup(unittest.TestCase):
    def test_real_fbx_parsing(self):
        fbx_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\pl_compound\models\fbx\mesh\c4s.fbx"
        if not os.path.exists(fbx_path):
            self.skipTest(f"Real test FBX file not found: {fbx_path}")
        refs = get_mesh_material_references(fbx_path)
        self.assertIn("weapons/models/c4/materials/weapon_c4.vmat", refs)
        self.assertIn("materials/models/weapons/v_models/c4/c4_panorama_control_panel.vmat", refs)

    def test_real_dmx_parsing(self):
        dmx_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\pl_compound\models\effects\urban_puddle_model02a_refs\mesh\urban_puddle_model02a_bg_body_lod0.dmx"
        if not os.path.exists(dmx_path):
            self.skipTest(f"Real test DMX file not found: {dmx_path}")
        refs = get_mesh_material_references(dmx_path)
        self.assertIn("materials/models/effects/urban_puddle01a.vmat", refs)

if __name__ == "__main__":
    unittest.main()
