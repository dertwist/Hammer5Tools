cmake_minimum_required(VERSION 3.20)
project(Hammer5Tools)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(Hammer5Tools WIN32 
    main.cpp
    request.cpp
    resources.rc
)

include(CTest)
if(BUILD_TESTING)
    add_executable(LauncherContractTests tests.cpp request.cpp)
    target_link_libraries(LauncherContractTests PRIVATE kernel32)
    add_test(NAME LauncherContractTests COMMAND LauncherContractTests)
endif()

target_include_directories(Hammer5Tools PRIVATE .)
target_compile_definitions(Hammer5Tools PRIVATE UNICODE _UNICODE)

target_link_libraries(Hammer5Tools PRIVATE 
    kernel32 
    user32 
    shell32 
    advapi32 
    shlwapi
)

set_target_properties(Hammer5Tools PROPERTIES 
    OUTPUT_NAME "Hammer5Tools"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

