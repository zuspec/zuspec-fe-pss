import os
from setuptools import Extension
def ext():
    extdir = os.path.dirname(os.path.abspath(__file__))
    return Extension("zuspec.fe.pss.ast", [
            os.path.join(extdir, 'ast.pyx'), os.path.join(extdir, 'PyBaseVisitor.cpp')
        ],
        include_dirs=[extdir],
        language="c++")
