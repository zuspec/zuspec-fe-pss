#*****************************************************************************
#* setup.py
#*
#* zuspec-parser Python extension setup file
#*****************************************************************************
import os
import sys
import platform
from setuptools import Extension, setup, find_namespace_packages

proj_dir = os.path.dirname(os.path.abspath(__file__))
pythondir = os.path.join(proj_dir, "python")

try:
    import sys
    sys.path.insert(0, os.path.join(proj_dir, "python/zuspec/fe/pss"))
    from __version__ import VERSION, BASE
    base = BASE
    version = VERSION
except Exception as e:
    print("NOTE: no version file found (%s)" % str(e))
    base = "0.0.1"
    version = base

isSrcBuild = False

try:
    from ivpm.setup import setup
    isSrcBuild = os.path.isdir(os.path.join(proj_dir, "src"))
    print("zuspec-parser: isSrcBuild: %s" % str(isSrcBuild))
except ImportError as e:
    from setuptools import setup
    print("zuspec-parser: not IVPM build (Falling back): %s" % str(e))

include_dirs = []

if isSrcBuild:
    include_dirs.append(pythondir)
    include_dirs.append(os.path.join(proj_dir, "src", "include"))
    include_dirs.append(os.path.join(proj_dir, "build", "include"))

library_dirs = []
libraries = []
extra_link_args = []

# TODO: in 'src' mode, must copy extension files

ast_ext = Extension(
    "zuspec.fe.pss.ast", 
    [
        os.path.join(pythondir, "ast.pyx"),
        os.path.join(pythondir, "PyBaseVisitor.cpp"),
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")
ext = Extension(
    "zuspec.fe.pss.core", 
    [ os.path.join(pythondir, "core.pyx"),
        os.path.join(pythondir, "PyParserUtils.cpp"),
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")

extensions=[ast_ext, ext]

setup_requires=['cython', 'ciostream', 'debug-mgr', 'ivpm']

if isSrcBuild:
    setup_requires.append('pyastbuilder')

setup_args = dict(
    name="zuspec-parser",
    packages=find_namespace_packages(where='python'),
    package_dir={'' : 'python' },
    package_data={
        'zuspec.fe.pss': [
            "ast.pyi",
            "ast.pxd",
            "ast_decl.pxd",
            "ast_ext.py",
            "core.pyi",
            "core.pxd",
            "decl.pxd",
        ]
    },
    version=version,
    author="Matthew Ballance",
    author_email="matt.ballance@gmail.com",
    description="Provides a PSS parser and related tools",
    long_description="""
    Zuspec parser
    """,
    ext_modules=extensions,
    entry_points={
        "ivpm.pkginfo": {
            'zuspec-parser = zuspec.fe.pss.pkginfo:PkgInfo'
        }
    },
    install_requires=[
        'debug-mgr',
        'ciostream'
    ],
    setup_requires=setup_requires,
)

if isSrcBuild:
    import shutil
    # Copy generated 'AST' extension files over before
    # attempting to build
    # for file in ('ast_decl.pxd', 'ast.pxd'):
    #     shutil.copyfile(
    #         os.path.join(proj_dir, "build", "zsp_ast", "ext", file),
    #         os.path.join(proj_dir, "python", "zsp_parser", file))
    # shutil.copyfile(
    #     os.path.join(proj_dir, "build", "zsp_ast", "ext", 'ast.pyx'),
    #     os.path.join(proj_dir, "python", 'ast.pyx'))

    setup_args["ivpm_extdep_pkgs"] = ["debug-mgr", "ciostream"]
    setup_args["ivpm_extdep_data"] = [
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'ast_decl.pxd'),
            os.path.join(proj_dir, "python", "zuspec", "fe", "pss", 'ast_decl.pxd')),
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'ast.pyi'),
            os.path.join(proj_dir, "python", "zuspec", "fe", "pss", 'ast.pyi')),
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'ast.pxd'),
            os.path.join(proj_dir, "python", "zuspec", "fe", "pss", 'ast.pxd')),
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'ast.pyx'),
            os.path.join(proj_dir, "python", 'ast.pyx')),
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'PyBaseVisitor.cpp'),
            os.path.join(proj_dir, "python", 'PyBaseVisitor.cpp')),
        (os.path.join(proj_dir, "build", "zsp_ast", "ext", 'PyBaseVisitor.h'),
            os.path.join(proj_dir, "python", 'PyBaseVisitor.h')),
    ]

    if platform.system() == "Linux":
        antlr4_rt_lib = None
        for libdir in ("lib", "lib64"):
            if os.path.exists("build/%s/libantlr4-runtime.so" % libdir):
                for f in os.listdir("build/%s" % libdir):
                    if f.startswith("libantlr4-runtime.so."):
                        antlr4_rt_lib = "build/{libdir}/%s" % f
                        break
            if antlr4_rt_lib is not None:
                break

        print("antlr4_rt_lib: %s" % antlr4_rt_lib)
#        antlr4_rt_lib = "build/{libdir}/{libpref}antlr4-runtime{dllext}"
    else:
        antlr4_rt_lib = "build/{libdir}/{libpref}antlr4-runtime{dllext}"

    setup_args["ivpm_extra_data"] = {
        "zuspec.fe.pss": [
            ("build/include", "share"),
            (antlr4_rt_lib, ""),
            ("build/{libdir}/{libpref}ast{dllext}", ""),
            ("build/{libdir}/{libpref}zsp-parser{dllext}", ""),
            ("python/PyBaseVisitor.h", "share/include"),
            ("python/PyParserUtils.h", "share/include"),
        ]
    }

setup(**setup_args)
