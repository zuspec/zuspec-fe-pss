#!/bin/sh -x

yum update -y
yum install -y glibc-static 
yum install -y java-11-openjdk-devel uuid-devel libuuid-devel

echo "BUILD_NUM=${BUILD_NUM}" >> python/zsp_parser/__build_num__.py
${IVPM_PYTHON} -m pip install -U ivpm cython setuptools

# Clean any stale download artifacts
rm -rf packages/.download

${IVPM_PYTHON} -m ivpm update -a --py-prerls-packages

# Verify ANTLR extraction
if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
    echo "ERROR: ANTLR C++ runtime not properly extracted"
    ls -la packages/antlr4-cpp-runtime/ || echo "Directory does not exist"
    exit 1
fi

if [ ! -f packages/antlr4-tools.jar ]; then
    echo "ERROR: ANTLR tools jar not downloaded"
    ls -la packages/ | grep antlr || echo "No ANTLR files found"
    exit 1
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
