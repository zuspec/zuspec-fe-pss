#****************************************************************************
#* CMakeLists.txt
#****************************************************************************
cmake_minimum_required (VERSION 3.5)

include(ExternalAntlr4Cpp)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-Wno-attributes)
  add_compile_options(-fPIC)
else()
  add_compile_options(-DANTLR4CPP_STATIC)
endif()

set(CMAKE_INSTALL_RPATH "$ORIGIN;$ORIGIN/../lib64")

include_directories(
    ${CMAKE_BINARY_DIR}/antlr4/include/antlr4-runtime
    ${PACKAGES_DIR}/antlr4-cpp-runtime/runtime/src
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSExprLexer
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSExprParser
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSLexer
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSParser
    ${CMAKE_BINARY_DIR}/zsp_ast/src/include
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    "${debug_mgr_INCDIR}"
    )

link_directories(
	${CMAKE_BINARY_DIR}/lib
	${CMAKE_BINARY_DIR}/lib64
	)

antlr_target(PSSExprLexer PSSExprLexer.g4 LEXER)
antlr_target(PSSExprParser PSSExprParser.g4 PARSER 
             DEPENDS_ANTLR PSSExprLexer
             COMPILE_FLAGS -lib ${ANTLR_PSSExprLexer_OUTPUT_DIR}
             VISITOR LISTENER)

antlr_target(PSSLexer PSSLexer.g4 LEXER)
antlr_target(PSSParser PSSParser.g4 PARSER 
             DEPENDS_ANTLR PSSLexer
             COMPILE_FLAGS -lib ${ANTLR_PSSLexer_OUTPUT_DIR}
             VISITOR LISTENER)

#********************************************************************
#* zsp
#********************************************************************
file(GLOB zsp_SRC
	"*.h"
	"*.cpp")
add_library(zsp-parser SHARED
	${zsp_SRC}
    pss_stdlib.h
	${ANTLR_PSSExprParser_OUTPUTS}
	${ANTLR_PSSExprLexer_OUTPUTS}
	${ANTLR_PSSParser_OUTPUTS}
	${ANTLR_PSSLexer_OUTPUTS})

install(TARGETS zsp-parser
    DESTINATION ${CMAKE_INSTALL_LIBDIR}
    EXPORT zsp-targets)

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/zsp" # source directory
    DESTINATION "include" # target directory
    FILES_MATCHING # install only matched files
    PATTERN "*.h" # select header files
)

add_dependencies(zsp-parser AST libantlr4)

if (WIN32)
	if (BUILD_SHARED_LIBS)
		list(APPEND ZUSPEC_PARSER_LIBS antlr4-runtime)
	else()
		list(APPEND ZUSPEC_PARSER_LIBS antlr4-runtime-static)
	endif()
else()
	list(APPEND ZUSPEC_PARSER_LIBS antlr4-runtime pthread)
endif()

target_link_libraries(zsp-parser ${ZUSPEC_PARSER_LIBS})
set_target_properties(zsp-parser PROPERTIES SKIP_BUILD_RPATH TRUE)

file(GLOB pss_stdlib_SRC "stdlib/*.pss")

add_custom_command(
    OUTPUT pss_stdlib.h
    DEPENDS ${pss_stdlib_SRC}
    COMMAND ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/stdlib/mk_pssstdlib.py
        ${CMAKE_CURRENT_BINARY_DIR}/pss_stdlib.h
)

# add_library(zsp-parser_static STATIC
# 	${zsp_SRC}
# 	${ANTLR_PSSParser_OUTPUTS}
# 	${ANTLR_PSSLexer_OUTPUTS})

# add_dependencies(zsp-parser_static AST libantlr4)
	
