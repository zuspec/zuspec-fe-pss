#****************************************************************************
#* CMakeLists.txt for ast
#****************************************************************************

cmake_minimum_required (VERSION 3.11)

project (ast)

file(GLOB_RECURSE ast_SRC
    "*.h"
    "*.cpp"
)

# Exclude subdirectories with dependencies and only include generated root files
list(FILTER ast_SRC EXCLUDE REGEX ".*/packages/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/python/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/python3/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/sav/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/src/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/tests/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/doc/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/docs/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/examples/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/scripts/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/resources/.*")
list(FILTER ast_SRC EXCLUDE REGEX ".*/etc/copyright\\.cpp$")
list(FILTER ast_SRC EXCLUDE REGEX ".*/CMakeFiles/.*")

set(CMAKE_CXX_STANDARD 14)

set(CompilerFlags
CMAKE_CXX_FLAGS
CMAKE_CXX_FLAGS_DEBUG
CMAKE_CXX_FLAGS_RELEASE
CMAKE_C_FLAGS
CMAKE_C_FLAGS_DEBUG
CMAKE_C_FLAGS_RELEASE
)
foreach(CompilerFlag ${CompilerFlags})
string(REPLACE "/MD" "/MT" ${CompilerFlag} "${${CompilerFlag}}")
string(REPLACE "/MDd" "/MTd" ${CompilerFlag} "${${CompilerFlag}}")
endforeach()

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
add_compile_options(-fPIC)
endif()


add_library(ast  SHARED ${ast_SRC})

target_include_directories(ast PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)


install(TARGETS ast
    DESTINATION ${CMAKE_INSTALL_LIBDIR}
    EXPORT ast-targets)

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/zsp"
    DESTINATION "include"
    COMPONENT dev
    FILES_MATCHING PATTERN "*.h")

