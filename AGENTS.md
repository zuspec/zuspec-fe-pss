
# Codex
You must prefix all commands with 'direnv exec . <command>' to get
a proper environment

# Build and run

Focus on Python and unit tests for now

% rm -rf build
% python setup.py build_ext --inplace
% pytest -s tests/python

Do not make assumptions about the number of cores. Use what is available.

## Changing the AST
Schema for the AST is in ast. It is processed by packages/pyastbuilder. 
This schema defines the data model created by parsing PSS code.
Any time an AST file is changed, the environment must be built from
scratch by removing the build directory and re-running cmake+make.

