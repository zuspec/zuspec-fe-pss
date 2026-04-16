"""Root conftest for zuspec-fe-pss tests.

Stubs pssparser if the native library is not available so that
pure-Python tests (e.g. SV lowering) can still run.
"""
import sys
import types

if "pssparser" not in sys.modules:
    try:
        import pssparser  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        _stub = types.ModuleType("pssparser")
        _stub.Parser = None
        _stub.ParseException = Exception
        sys.modules["pssparser"] = _stub

        _ast = types.ModuleType("pssparser.ast")
        sys.modules["pssparser.ast"] = _ast

        _core = types.ModuleType("pssparser.core")

        class _FakeFactory:
            @staticmethod
            def inst():
                return _FakeFactory()
            def getDebugMgr(self):
                class _Dbg:
                    def enable(self, v): pass
                return _Dbg()

        _core.Factory = _FakeFactory
        sys.modules["pssparser.core"] = _core
