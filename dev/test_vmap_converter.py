import os
import sys
import shutil
import unittest
from pathlib import Path

# Set up paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.dotnet import decompile_model_to_glb
from src.editors.smartprop_editor.vmap_vsmart_converter import scan_vmap_for_props, convert_vmap_props_to_vsmart
from src.common import get_cs2_path

class TestVMapConverter(unittest.TestCase):
    """
    Unit test suite to verify model decompilation, VMAP scanning,
    and VMAP-VSMART conversion routines.
    """
    def setUp(self):
        self.test_vmap = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_ober\maps\vsmart_test.vmap"
        self.scratch_dir = os.path.join(project_root, "scratch")
        os.makedirs(self.scratch_dir, exist_ok=True)
        
        self.copied_vmap = os.path.join(self.scratch_dir, "vsmart_test_temp.vmap")
        self.output_vsmart = os.path.join(self.scratch_dir, "smartprops", "test_vsmart_output.vsmart")
        
        # Prepare VMAP copy if original exists
        if os.path.exists(self.test_vmap):
            shutil.copy2(self.test_vmap, self.copied_vmap)

    def tearDown(self):
        # Clean up temporary test files
        for p in [self.copied_vmap, self.output_vsmart]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass
        smartprop_dir = os.path.join(self.scratch_dir, "smartprops")
        if os.path.exists(smartprop_dir):
            try:
                shutil.rmtree(smartprop_dir)
            except:
                pass

    def test_01_model_decompilation(self):
        """Test model decompilation to GLB."""
        print("\n--- Running Model Decompilation Test ---")
        model_path = "models/cs_italy/props/barrel/italy_barrel_wood_1.vmdl"
        
        # This will trigger decompile (either from VPK or cache)
        glb_path = decompile_model_to_glb(model_path)
        
        self.assertIsNotNone(glb_path, "Decompilation failed to return a GLB path")
        self.assertTrue(os.path.exists(glb_path), f"Decompiled GLB file does not exist: {glb_path}")
        self.assertTrue(glb_path.endswith(".glb"), "Output file does not have .glb extension")
        print(f"Decompilation success! GLB saved at: {glb_path} (Size: {os.path.getsize(glb_path)} bytes)")

    def test_02_vmap_scanning(self):
        """Test scanning a VMAP for prop entities."""
        print("\n--- Running VMAP Scanning Test ---")
        if not os.path.exists(self.test_vmap):
            self.skipTest(f"Test VMAP file not found: {self.test_vmap}")
            
        props = scan_vmap_for_props(self.test_vmap)
        self.assertIsInstance(props, list, "Props list should be a list object")
        self.assertGreater(len(props), 0, "No props were found in the scanned map")
        
        # Inspect the first prop
        prop = props[0]
        self.assertIn("classname", prop)
        self.assertIn("model", prop)
        self.assertIn("origin", prop)
        self.assertIn("angles", prop)
        self.assertIn("scales", prop)
        print(f"Scanned {len(props)} props successfully. First prop class: {prop['classname']}, model: {prop['model']}")

    def test_03_vmap_to_vsmart_conversion(self):
        if not os.path.exists(self.test_vmap):
            self.skipTest(f"Test VMAP file not found: {self.test_vmap}")
            
        # 1. Scan props first to get indices
        props = scan_vmap_for_props(self.copied_vmap)
        selected_indices = list(range(len(props))) # select all
        
        # Force garbage collection to release file handles immediately
        import gc; gc.collect()
        try:
            import System
            System.GC.Collect()
            System.GC.WaitForPendingFinalizers()
        except:
            pass
        
        # 2. Run conversion on the copied VMAP
        success = convert_vmap_props_to_vsmart(
            vmap_path=self.copied_vmap,
            selected_indices=selected_indices,
            output_vsmart_path=self.output_vsmart,
            pivot_strategy="center"
        )
        
        self.assertTrue(success, "Converter reported failure during conversion")
        self.assertTrue(os.path.exists(self.output_vsmart), "Output VSMART file was not created")
        
        # 3. Read output VSMART to check structure
        with open(self.output_vsmart, "r") as f:
            vsmart_content = f.read()
        self.assertIn("generic_data_type = \"CSmartPropRoot\"", vsmart_content, "VSMART file does not have correct root class")
        self.assertIn("CSmartPropElement_Model", vsmart_content, "VSMART file does not contain model element declarations")
        
        # 4. Scan updated map to verify original props were deleted and subclass_prop_smart added
        updated_props = scan_vmap_for_props(self.copied_vmap)
        
        # The scan_vmap_for_props collects props (prop_static, prop_dynamic, subclass_prop_smart)
        # Check if the subclass_prop_smart exists in the updated props list
        smartprop_count = 0
        for p in updated_props:
            if p["classname"] == "subclass_prop_smart":
                smartprop_count += 1
                
        self.assertEqual(smartprop_count, 1, "There should be exactly one subclass_prop_smart entity in the map")
        self.assertEqual(len(updated_props), 1, "Only the subclass_prop_smart entity should remain in the map")
        print("Conversion and replacement test passed successfully!")

if __name__ == "__main__":
    unittest.main()
