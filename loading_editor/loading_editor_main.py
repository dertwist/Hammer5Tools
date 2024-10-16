# This Python file uses the following encoding: utf-8
import os, shutil, pathlib, subprocess,time
from basic_operations import normalize_name, random_char

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QProgressBar, QDialog, QVBoxLayout
from preferences import get_config_value, get_cs2_path, get_addon_name, debug
from loading_editor.ui_loading_editor_mainwindow import Ui_Loading_editorMainWindow
from loading_editor.svg_drag_and_drop import Svg_Drag_and_Drop
from explorer.image_viewer import ImageViewer

class ApplyScreenshots:
    def __init__(self, game_screenshot_path, content_screenshot_path):
        self.game_screenshot_path = game_screenshot_path
        self.content_screenshot_path = content_screenshot_path
        debug(f'game screenshots path: {self.game_screenshot_path}')
        debug(f'content screenshots path: {self.content_screenshot_path}')

        self.addon_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())

        debug(f'addon_path path: {self.addon_path}')

        self.copy_files()
        self.rename_files()




        # Collect image files from content folder
        file_list = []
        for root, dirs, files in os.walk(self.content_screenshot_path):
            for file_name in files:
                full_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(full_file_path, self.addon_path)
                file_list.append(relative_path)
        debug(f'File list: {file_list}')

        # Delete old vtex files
        try:
            shutil.rmtree(os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p"))
        except:
            pass

        #Process
        for item in file_list:
            print(f'Processing: {item}')
            self.creating_vtex(item)

    def copy_files(self):
        shutil.rmtree(self.content_screenshot_path)
        shutil.copytree(self.game_screenshot_path, self.content_screenshot_path)

    def rename_files(self):
        base_path = self.content_screenshot_path
        for file_images_loop_count, file_name in enumerate(os.listdir(base_path)):
            try:
                if file_images_loop_count == 0:
                    file_name_parts = os.path.splitext(file_name)
                    file_extension = file_name_parts[1]
                    new_file_name = f"{get_addon_name()}_png{file_extension}"
                    debug(f'Old name {file_name}, New name {new_file_name}')
                    os.rename(os.path.join(base_path, file_name), os.path.join(base_path, new_file_name))
                else:
                    file_name_parts = os.path.splitext(file_name)
                    file_extension = file_name_parts[1]
                    new_file_name = f"{get_addon_name()}_{file_images_loop_count}_png{file_extension}"
                    debug(f'Old name {file_name}, New name {new_file_name}')
                    os.rename(os.path.join(base_path, file_name), os.path.join(base_path, new_file_name))
            except Exception as e:
                print(f"An error occurred while renaming the file: {file_name}. Error: {e}")


    def creating_vtex(self, path):
        vtex_file = """<!-- dmx encoding keyvalues2_noids 1 format vtex 1 -->
                        "CDmeVtex"
                        {
                            "m_inputTextureArray" "element_array"
                            [
                                "CDmeInputTexture"
                                {
                                    "m_name" "string" "SheetTexture"
                                    "m_fileName" "string" "%%PATH%%"
                                    "m_colorSpace" "string" "linear"
                                    "m_typeString" "string" "2D"
                                    "m_imageProcessorArray" "element_array"
                                    [
                                    ]
                                }
                            ]
                            "m_outputTypeString" "string" "2D"
                            "m_outputFormat" "string" "BC7"
                            "m_outputClearColor" "vector4" "0 0 0 0"
                            "m_nOutputMinDimension" "int" "0"
                            "m_nOutputMaxDimension" "int" "2048"
                            "m_textureOutputChannelArray" "element_array"
                            [
                                "CDmeTextureOutputChannel"
                                {
                                    "m_inputTextureArray" "string_array"
                                    [
                                        "SheetTexture"
                                    ]
                                    "m_srcChannels" "string" "rgba"
                                    "m_dstChannels" "string" "rgba"
                                    "m_mipAlgorithm" "CDmeImageProcessor"
                                    {
                                        "m_algorithm" "string" ""
                                        "m_stringArg" "string" ""
                                        "m_vFloat4Arg" "vector4" "0 0 0 0"
                                    }
                                    "m_outputColorSpace" "string" "linear"
                                }
                            ]
                            "m_vClamp" "vector3" "0 0 0"
                            "m_bNoLod" "bool" "1"
                        }
                        """
        vtex_file = vtex_file.replace('%%PATH%%', path.replace('\\', '/'))
        name = os.path.basename(path)
        name = os.path.splitext(name)[0]
        path = os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p", f'{name}.vtex')
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as file:
            file.write(vtex_file)
class Loading_editorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Loading_editorMainWindow()
        self.ui.setupUi(self)

        game_screenshot_path = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), 'screenshots')
        content_screenshot_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), 'screenshots')
        if os.path.exists(game_screenshot_path):
            pass
        else:
            os.makedirs(game_screenshot_path)

        # Explorer init
        explorer_view = ImageViewer(tree_directory=game_screenshot_path)
        explorer_view.setStyleSheet("padding:0")
        self.ui.explorer.layout().addWidget(explorer_view)
        self.ui.screenshot_preview.layout().addWidget(explorer_view.image_label)

        self.Svg_Drap_and_Drop_Area = Svg_Drag_and_Drop()
        self.ui.svg_icon_frame.layout().addWidget(self.Svg_Drap_and_Drop_Area)

        # apply_description_button
        self.ui.apply_description_button.clicked.connect(self.do_loading_editor_cs2_description)
        # apply images
        self.ui.apply_screenshots_button.clicked.connect(lambda : ApplyScreenshots(game_screenshot_path=game_screenshot_path, content_screenshot_path=content_screenshot_path))
        self.ui.apply_icon_button.clicked.connect(self.icon_processs)

        self.ui.clear_all_button.clicked.connect(self.clear_images)
        self.ui.open_folder_button.clicked.connect(self.open_images_folder)

    def clear_images(self):
        game_screenshot_path = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), 'screenshots')
        shutil.rmtree(game_screenshot_path)
        os.makedirs(game_screenshot_path)
    def open_images_folder(self):
        game_screenshot_path = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), 'screenshots')
        os.startfile(game_screenshot_path)

    def loading_editor_cs2_description(self, loading_editor_cs2_description_text):
        file_name = get_cs2_path() + '\\' + r"game\csgo_addons" + '\\' + str(
            get_addon_name()) + '\\' + 'maps' + '\\' + str(get_addon_name()) + '.txt'
        print(file_name)
        with open(file_name, 'w') as f:
            f.write("COMMUNITYMAPCREDITS:\n")
            f.write(loading_editor_cs2_description_text)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Loading_editorMainWindow()
    window.show()
    sys.exit(app.exec())