#!/bin/sh -x

yum update -y
yum install -y glibc-static 
yum install -y java-11-openjdk-devel uuid-devel libuuid-devel

echo "BUILD_NUM=${BUILD_NUM}" >> python/zsp_parser/__build_num__.py
${IVPM_PYTHON} -m pip install -U ivpm cython setuptools

${IVPM_PYTHON} -m ivpm update -a --py-prerls-packages

# Workaround for ivpm zip extraction issue - manually extract ANTLR C++ runtime if needed
if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
    echo "ANTLR C++ runtime extraction incomplete, manually extracting..."
    cd packages
    # Download the zip file if it doesn't exist
    if [ ! -f antlr4-cpp-runtime-source.zip ]; then
        curl -L -o antlr4-cpp-runtime-source.zip https://www.antlr.org/download/antlr4-cpp-runtime-4.13.2-source.zip
    fi
    # Remove the incomplete directory
    rm -rf antlr4-cpp-runtime
    # Extract fresh
    unzip -q antlr4-cpp-runtime-source.zip -d antlr4-cpp-runtime
    cd ..
fi

# Verify ANTLR extraction
if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
    echo "ERROR: ANTLR C++ runtime not properly extracted"
    ls -la packages/antlr4-cpp-runtime/ || echo "Directory does not exist"
    exit 1
fi

if [ ! -f packages/antlr4-tools.jar ]; then
    echo "ERROR: ANTLR tools jar not downloaded"
    ls -la packages/ | grep antlr || echo "No ANTLR files found"
    # Try downloading manually
    cd packages
    curl -L -o antlr4-tools.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
    cd ..
    # Verify again
    if [ ! -f packages/antlr4-tools.jar ]; then
        echo "ERROR: Failed to download ANTLR tools jar"
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
