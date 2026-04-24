cmake_minimum_required(VERSION 3.20)
project(FileEdit)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(FileEdit WIN32 
    main.cpp 
    resources.rc
)

target_include_directories(FileEdit PRIVATE .)

target_link_libraries(FileEdit PRIVATE 
    kernel32 
    user32 
    shell32 
    advapi32 
    shlwapi
)

set_target_properties(FileEdit PROPERTIES 
    OUTPUT_NAME "fileedit"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

