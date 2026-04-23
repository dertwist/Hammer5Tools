cmake_minimum_required(VERSION 3.20)
project(Hammer5ToolsUpdater)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Source files
if(MINGW)
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static -static-libgcc -static-libstdc++")
endif()
set(SOURCES 
    main.cpp 
    update_logic.cpp 
    update_logic.h
    resources.rc
)

add_executable(Hammer5ToolsUpdater WIN32 ${SOURCES})

target_link_libraries(Hammer5ToolsUpdater PRIVATE kernel32 user32 shell32 winhttp)
target_compile_definitions(Hammer5ToolsUpdater PRIVATE UNICODE _UNICODE _WIN32_WINNT=0x0600)

set_target_properties(Hammer5ToolsUpdater PROPERTIES 
    OUTPUT_NAME "Hammer5ToolsUpdater"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
