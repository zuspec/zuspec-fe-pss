#!/bin/sh -x

yum update -y
yum install -y glibc-static 
yum install -y java-11-openjdk-devel uuid-devel libuuid-devel

echo "BUILD_NUM=${BUILD_NUM}" >> python/zuspec/fe/pss/__build_num__.py

${IVPM_PYTHON} -m pip install -U ivpm cython setuptools

# Run ivpm update; antlr4-cpp-runtime may fail to extract due to nested
# cmake _deps paths in the zip -- we handle that below.
${IVPM_PYTHON} -m ivpm update -a --py-prerls-packages || true

# The antlr4-cpp-runtime zip contains runtime/_deps/googletest-src/... paths
# that fail to extract in some manylinux containers.  Re-extract manually,
# skipping those unneeded cmake-fetched test deps.
if [ ! -f packages/antlr4-cpp-runtime/CMakeLists.txt ]; then
    echo "antlr4-cpp-runtime CMakeLists.txt missing -- re-extracting zip"
    ANTLR4_URL=https://www.antlr.org/download/antlr4-cpp-runtime-4.13.2-source.zip
    ANTLR4_ZIP=/tmp/antlr4-cpp-runtime.zip
    curl -L -o "${ANTLR4_ZIP}" "${ANTLR4_URL}"
    rm -rf packages/antlr4-cpp-runtime
    mkdir -p packages/antlr4-cpp-runtime
    ${IVPM_PYTHON} -c "
from zipfile import ZipFile
import os
with ZipFile('${ANTLR4_ZIP}', 'r') as z:
    for info in z.infolist():
        if not info.filename.startswith('runtime/_deps'):
            z.extract(info, 'packages/antlr4-cpp-runtime')
"
fi

PYTHON=./packages/python/bin/python
${PYTHON} -m pip install twine auditwheel ninja wheel cython
${PYTHON} -m pip install debug-mgr

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
