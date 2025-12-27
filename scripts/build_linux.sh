#!/bin/sh -x

yum update -y
yum install -y glibc-static 
yum install -y java-11-openjdk-devel uuid-devel libuuid-devel

echo "BUILD_NUM=${BUILD_NUM}" >> python/zsp_parser/__build_num__.py

# Install ivpm with zip extraction fixes
${IVPM_PYTHON} -m pip install -U git+https://github.com/mballance/ivpm.git@fix-zip-extraction cython setuptools

# Run ivpm update - should now work properly with the race condition fix
${IVPM_PYTHON} -m ivpm update -a --py-prerls-packages

# Debug: Check what's actually in the ANTLR directory
echo "=== DEBUG START ==="
echo "Checking packages/antlr4-cpp-runtime directory..."
ls -la packages/antlr4-cpp-runtime/
echo "Looking for CMakeLists.txt..."
find packages/antlr4-cpp-runtime -name "CMakeLists.txt" -type f 2>&1
echo "=== DEBUG END ==="

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
