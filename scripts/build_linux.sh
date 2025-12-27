#!/bin/sh -x

yum update -y
yum install -y glibc-static 
yum install -y java-11-openjdk-devel uuid-devel libuuid-devel

echo "BUILD_NUM=${BUILD_NUM}" >> python/zsp_parser/__build_num__.py

# Install fixed ivpm with race condition fix from our fork
${IVPM_PYTHON} -m pip install -U git+https://github.com/mballance/ivpm.git@fix-download-race-condition cython setuptools

# Run ivpm update - should now work without .download conflicts
# But allow it to fail since ANTLR zip extraction has issues in ivpm
${IVPM_PYTHON} -m ivpm update -a --py-prerls-packages || echo "ivpm update had some failures, will verify critical packages..."

# Verify and fix ANTLR if needed (ivpm has zip extraction issues)
if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
    echo "ANTLR C++ runtime not properly extracted by ivpm, fixing..."
    cd packages
    if [ ! -f antlr4-cpp-runtime-source.zip ]; then
        curl -L -o antlr4-cpp-runtime-source.zip https://www.antlr.org/download/antlr4-cpp-runtime-4.13.2-source.zip
    fi
    rm -rf antlr4-cpp-runtime
    mkdir -p antlr4-cpp-runtime
    unzip -q antlr4-cpp-runtime-source.zip -d antlr4-cpp-runtime
    cd ..
    # Verify it worked
    if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
        echo "ERROR: Failed to extract ANTLR C++ runtime"
        exit 1
    fi
fi

PYTHON=./packages/python/bin/python
${PYTHON} -m pip install twine auditwheel ninja wheel cython

echo "IVPM version: (1)"
${PYTHON} -m pip show ivpm

${PYTHON} -m pip install -U ivpm

echo "IVPM version: (2)"
${PYTHON} -m pip show ivpm

# First, do all the required code generation. This ensures the
# Python package can be imported during final package build
${PYTHON} setup.py build_ext --inplace

${PYTHON} setup.py bdist_wheel

for whl in dist/*.whl; do
    ${PYTHON} -m auditwheel repair --only-plat $whl
    if test $? -ne 0; then exit 1; fi
    rm $whl
done
