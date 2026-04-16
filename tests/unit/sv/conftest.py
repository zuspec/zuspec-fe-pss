"""Shared fixtures for PSS-to-SV lowering tests.

Stubs out pssparser so tests run without the native parser library.
"""
import sys
import types

# Stub pssparser so zuspec.fe.pss can be imported without native lib
if "pssparser" not in sys.modules:
    _stub = types.ModuleType("pssparser")
    _stub.Parser = None
    _stub.ParseException = Exception
    sys.modules["pssparser"] = _stub
    _ast = types.ModuleType("pssparser.ast")
    sys.modules["pssparser.ast"] = _ast
