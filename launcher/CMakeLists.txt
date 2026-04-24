cmake_minimum_required(VERSION 3.20)
project(Hammer5ToolsLauncher)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(Hammer5ToolsLauncher WIN32 
    main.cpp 
    resources.rc
)

target_include_directories(Hammer5ToolsLauncher PRIVATE .)

target_link_libraries(Hammer5ToolsLauncher PRIVATE 
    kernel32 
    user32 
    shell32 
    advapi32 
    shlwapi
)

set_target_properties(Hammer5ToolsLauncher PROPERTIES 
    OUTPUT_NAME "Hammer5ToolsHandler"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
