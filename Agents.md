
# Build and run

Focus on cmake and googletest-based unit tests for now. 

% mkdir -p build
% cd build
% cmake .. -DCMAKE_BUILD_TYPE=Debug
% make -j$(nproc)

Do not make assumptions about the number of cores. Use what is available.

You can run tests from the build area:
% LD_LIBRARY_PATH=$(pwd)/lib ./tests/zsp_testmain 

## Changing the AST
Schema for the AST is in ast. It is processed by packages/pyastbuilder. 
This schema defines the data model created by parsing PSS code.
Any time an AST file is changed, the environment must be built from
scratch by removing the build directory and re-running cmake+make.

