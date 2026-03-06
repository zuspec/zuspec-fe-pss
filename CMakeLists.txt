cmake_minimum_required (VERSION 3.11)

project(zuspec-parser)

include(ExternalProject)

set(CMAKE_INSTALL_RPATH $ORIGIN)

if (NOT PACKAGES_DIR)
  set(PACKAGES_DIR ${CMAKE_SOURCE_DIR}/packages)

  set(ENABLE_TESTS True)

endif()

if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  message("Set CMAKE_INSTALL_PREFIX")
  set (CMAKE_INSTALL_PREFIX ${CMAKE_BINARY_DIR})
else()
  message("CMAKE_INSTALL_PREFIX set to ${CMAKE_INSTALL_PREFIX}")
endif()


message("PSSParser: PACKAGES_DIR=${PACKAGES_DIR}")


list(APPEND CMAKE_MODULE_PATH ${PACKAGES_DIR}/antlr4-cpp-runtime/cmake)

# Some include	
include_directories(${CMAKE_BINARY_DIR}/zsp_ast/src/include)

link_directories(
	${CMAKE_BINARY_DIR}/antlr4/lib
	${CMAKE_BINARY_DIR}/zsp_ast/lib
	)

set(ANTLR_EXECUTABLE ${PACKAGES_DIR}/antlr4-tools.jar)
set(ANTLR4_JAR_LOCATION ${PACKAGES_DIR}/antlr4-tools.jar)

if (WIN32)
  set(PYTHON ${PACKAGES_DIR}/python/Scripts/python.exe)
else()
  set(PYTHON ${PACKAGES_DIR}/python/bin/python)
endif()

find_package(ANTLR REQUIRED)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS True)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  set(ANTLR_CXXFLAGS "-Wno-attributes -fPIC")
else()
  set(ANTLR_CXXFLAGS -DANTLR4CPP_STATIC)
endif()

#add_compile_options(-pg)
#add_link_options(-pg)

set(CompilerFlags
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELEASE
        "-fPIC"
        )
foreach(CompilerFlag ${CompilerFlags})
  string(REPLACE "/MD" "/MT" ${CompilerFlag} "${${CompilerFlag}}")
  string(REPLACE "/MDd" "/MTd" ${CompilerFlag} "${${CompilerFlag}}")
endforeach()

execute_process(COMMAND ${PYTHON} -m ivpm share cmake OUTPUT_VARIABLE IVPM_CMAKE_PATH)
list(APPEND CMAKE_MODULE_PATH ${IVPM_CMAKE_PATH})
message("IVPM_CMAKE_PATH: ${IVPM_CMAKE_PATH} ${CMAKE_MODULE_PATH}")

include(ivpm)

execute_process(
    COMMAND ${PYTHON} -c "import debug_mgr, os; print(os.path.join(os.path.dirname(debug_mgr.__file__), 'share', 'include'))"
    OUTPUT_VARIABLE debug_mgr_INCDIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
execute_process(
    COMMAND ${PYTHON} -c "import debug_mgr, os; print(os.path.dirname(debug_mgr.__file__))"
    OUTPUT_VARIABLE debug_mgr_LIBDIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
message("Set: debug_mgr_INCDIR=${debug_mgr_INCDIR}")
message("Set: debug_mgr_LIBDIR=${debug_mgr_LIBDIR}")

message("Note: CMAKE_INSTALL_PREFIX set to ${CMAKE_INSTALL_PREFIX}")

ExternalProject_Add(libantlr4
    PREFIX antlr4
    SOURCE_DIR "${PACKAGES_DIR}/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
      -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_INSTALL_PREFIX}
      -DCMAKE_INTALL_LIBDIR:PATH=${CMAKE_INSTALL_LIBDIR}
      -DCMAKE_CXX_FLAGS:STRING=${ANTLR_CXXFLAGS}
      -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
      -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
      -DBUILD_STATIC_LIBS:BOOL=False
      -DCMAKE_OSX_ARCHITECTURES:STRING=${CMAKE_OSX_ARCHITECTURES}
      -DCMAKE_POLICY_VERSION_MINIMUM:STRING=3.5
    )

#	${PYTHON} ${CMAKE_SOURCE_DIR}/try.py
#		${PYTHON} -m astbuilder gen-cpp -name ast -namespace zsp::ast -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -license ${CMAKE_CURRENT_SOURCE_DIR}/etc/copyright.cpp &&
#		${PYTHON} -m astbuilder gen-pyext -name ast -namespace zsp::ast -package zsp_parser.ast -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -o ../ext
     
ExternalProject_Add(AST
	PREFIX zsp_ast
	SOURCE_DIR "${CMAKE_CURRENT_BINARY_DIR}/zsp_ast/src"
	DOWNLOAD_COMMAND 
        ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/gen_ast.py
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_INSTALL_PREFIX}
        -DCMAKE_INTALL_LIBDIR:PATH=${CMAKE_INSTALL_LIBDIR}
        -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
        -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
        -DCMAKE_OSX_ARCHITECTURES:STRING=${CMAKE_OSX_ARCHITECTURES}
	)

add_subdirectory(src)


if (ENABLE_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

#if (NOT DEFINED ENV{EXT_PYTHON})
#   set(ENV{EXT_PYTHON} ${PYTHON})
#endif()

#add_custom_target(build_ext ALL
#	COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_BINARY_DIR}/pssast/ext/pssast_decl.pxd ${CMAKE_CURRENT_SOURCE_DIR}/python/pssparser/pssast_decl.pxd
#	COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_BINARY_DIR}/pssast/ext/pssast.pxd ${CMAKE_CURRENT_SOURCE_DIR}/python/pssparser/pssast.pxd
#	COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_BINARY_DIR}/pssast/ext/pssast.pyx ${CMAKE_CURRENT_SOURCE_DIR}/python/pssast.pyx
#	COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_BINARY_DIR}/pssast/ext/PyBaseVisitor.cpp ${CMAKE_CURRENT_SOURCE_DIR}/python/PyBaseVisitor.cpp
#	COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_BINARY_DIR}/pssast/ext/PyBaseVisitor.h ${CMAKE_CURRENT_SOURCE_DIR}/python/PyBaseVisitor.h
#	COMMAND ${CMAKE_COMMAND} -E env CMAKE_BINARY_DIR=${CMAKE_BINARY_DIR} $ENV{EXT_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py build_ext --inplace
#	COMMAND $ENV{EXT_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py bdist_wheel
#	)
