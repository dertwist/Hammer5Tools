cmake_minimum_required(VERSION 3.20)
project(Hammer5ToolsLauncher)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Using MinGW or MSVC
if(MINGW)
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static -static-libgcc -static-libstdc++")
endif()
add_executable(Hammer5ToolsLauncher WIN32 main.cpp resources.rc)

target_link_libraries(Hammer5ToolsLauncher PRIVATE kernel32 user32 shell32 advapi32)

set_target_properties(Hammer5ToolsLauncher PROPERTIES 
    OUTPUT_NAME "Hammer5Tools"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
