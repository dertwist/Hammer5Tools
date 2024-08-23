# This Python file uses the following encoding: utf-8
import os, shutil, pathlib, subprocess,time
from basic_operations import normalize_name, random_char

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QProgressBar, QDialog, QVBoxLayout
from preferences import get_config_value, get_cs2_path, get_addon_name
from loading_editor.ui_loading_editor_mainwindow import Ui_Loading_editorMainWindow
from loading_editor.loading_editor_image_drag_and_drop_area import loading_editor_image_drag_and_drop_area_window
from loading_editor.svg_drag_and_drop import Svg_Drag_and_Drop

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Progress")
        self.setModal(True)
        self.layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar)

class Loading_editorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Loading_editorMainWindow()
        self.ui.setupUi(self)
        self.loading_editor_image_drag_and_drop_area_window = loading_editor_image_drag_and_drop_area_window()
        self.ui.Loading_editor_tab_images_import.layout().addWidget(self.loading_editor_image_drag_and_drop_area_window)

        self.Svg_Drap_and_Drop_Area = Svg_Drag_and_Drop()
        self.ui.svg_icon_frame.layout().addWidget(self.Svg_Drap_and_Drop_Area)

        # apply_description_button
        self.ui.apply_description_button.clicked.connect(self.do_loading_editor_cs2_description)
        # apply images
        self.ui.apply_images_button.clicked.connect(self.do_loadin_editor_cs2_images)
        self.ui.apply_icon_button.clicked.connect(self.icon_processs)

    def loading_editor_cs2_description(self, loading_editor_cs2_description_text):
        file_name = get_cs2_path() + '\\' + r"game\csgo_addons" + '\\' + str(
            get_addon_name()) + '\\' + 'maps' + '\\' + str(get_addon_name()) + '.txt'
        print(file_name)
        with open(file_name, 'w') as f:
            f.write("COMMUNITYMAPCREDITS:\n")
            f.write(loading_editor_cs2_description_text)

    def loadin_editor_cs2_images(self, loadin_editor_cs2_images_images):
        # Create and show progress dialog
        self.progress_dialog = ProgressDialog(self)
        total_images = len(loadin_editor_cs2_images_images)
        self.progress_dialog.progress_bar.setMaximum(total_images)

        self.progress_dialog.show()
        self.progress_dialog.progress_bar.setValue(1)


        # paths
        # remove old images
        try:
            shutil.rmtree(
                get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p' + "\\")
            os.makedirs(
                get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p' + "\\",
                exist_ok=True)
        except:
            os.makedirs(
                get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p' + "\\",
                exist_ok=True)

        # Initialize progress bar


        # add images
        for i in range(total_images):
            image_path = loadin_editor_cs2_images_images[i]
            image_extension = pathlib.Path(os.path.basename(image_path)).suffix
            image_name = normalize_name(pathlib.Path(os.path.basename(image_path)).stem) + random_char(6)

            image_dst = get_cs2_path() + r"\content\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots' + '\\' + str(
                i) + '_' + str(image_name + image_extension)

            # copy images
            try:
                shutil.copy2((image_path), (image_dst))
            except:
                os.makedirs(
                    get_cs2_path() + r"\content\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots')
                shutil.copy2((image_path), (image_dst))
            # create vmat
            vmat_file_path = get_cs2_path() + r"\content\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots' + '\\' + str(
                i) + '_' + str(image_name) + '.vmat'
            vmat_content = """
            // THIS FILE IS AUTO-GENERATED

            Layer0
            {
                shader "csgo_composite_generic.vfx"

                g_flAlphaBlend "0.000"

                //---- Options ----
                TextureA "hammer5tools_screenshots/%%NAME%%IMAGE%%"
                TextureB ""

                UnusedVariables
                {
                    "g_flBumpStrength" "1"
                    "TextureNormal" ""
                    "g_nTextureAddressModeU" "0"
                    "g_nTextureAddressModeV" "0"
                }


                VariableState
                {
                    ""
                    {
                    }
                    "Options"
                    {
                    }
                }
            }
            """
            vmat_content = vmat_content.replace("%%NAME%%IMAGE%%", (str(i) + '_' + image_name + image_extension))
            with open(vmat_file_path, 'w') as f:
                f.write(vmat_content)
            # compilation
            subprocess.run('"' + get_cs2_path() + r"\game\bin\win64\resourcecompiler.exe" + '"' + " -i " + '"' + str(
                vmat_file_path) + '"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Update progress bar
            self.progress_dialog.progress_bar.setValue(i + 1)
            QApplication.processEvents()  # Allow the GUI to process events

        # move images
        for file_name in os.listdir(
                get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots'):
            source_dir = get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots'
            target_dir = get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p'
            if pathlib.Path(file_name).suffix == '.vtex_c':
                shutil.move(os.path.join(source_dir, file_name), target_dir)

        # rename images
        file_images_loop_count = 0
        for file_name in os.listdir(
                get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p'):
            folder_path = get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\panorama\images\map_icons\screenshots\1080p' + '\\'

            if file_images_loop_count == 0:
                os.rename(str(folder_path + file_name), str(folder_path + get_addon_name() + "_png" + ".vtex_c"))
            else:
                os.rename(str(folder_path + file_name),
                          str(folder_path + get_addon_name() + "_" + str(file_images_loop_count) + "_png" + ".vtex_c"))
                pass
            file_images_loop_count = file_images_loop_count + 1

        # cleanup
        shutil.rmtree(get_cs2_path() + r"\game\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots')
        shutil.rmtree(get_cs2_path() + r"\content\csgo_addons" + '\\' + get_addon_name() + r'\hammer5tools_screenshots')

        # Close progress dialog
        self.progress_dialog.close()

    def icon_processs(self):
        svg_path = self.Svg_Drap_and_Drop_Area.loading_editor_get_svg()
        svg_path = os.path.normpath(svg_path)
        folder_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), "panorama", "images", "map_icons")

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        svg_dst = os.path.join(folder_path, "map_icon_" + get_addon_name() + ".svg")
        print(svg_dst)
        if os.path.exists(svg_dst):
            os.remove(svg_dst)
        shutil.copy2(svg_path, svg_dst)

    def do_loading_editor_cs2_description(self):
        self.loading_editor_cs2_description(self.ui.PlainTextEdit_Description_2.toPlainText())

    def do_loadin_editor_cs2_images(self):
        images = self.loading_editor_image_drag_and_drop_area_window.loading_editor_get_all_images()
        self.loadin_editor_cs2_images(images)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Loading_editorMainWindow()
    window.show()
    sys.exit(app.exec())