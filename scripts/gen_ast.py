import os
import sys
import platform
import subprocess

def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.dirname(scripts_dir)

    if os.path.isdir(os.path.join(proj_dir, "packages")):
        packages_dir = os.path.join(proj_dir, "packages")
    else:
        packages_dir = os.path.dirname(proj_dir)

    print("proj_dir: %s" % str(proj_dir), flush=True)
    print("packages_dir: %s" % str(packages_dir), flush=True)

    sys.path.insert(0, os.path.join(packages_dir, "pyastbuilder", "src"))

    print("PYTHONPATH: %s" % str(sys.path), flush=True)

    env = os.environ.copy()
    ps = ";" if platform.system() == "Windows" else ":"
    env["PYTHONPATH"] = ps.join(sys.path)

    try:
        import astbuilder
    except ImportError as e:
        print("Failed to import astbuilder: %s" % str(e))
    
    if os.path.exists("zsp_ast.d"):
        print("Checking timestamps")
        for f in os.listdir(os.path.join(proj_dir, "ast")):
            print("File: %s" % f)

    cmd = [sys.executable, "-m", "astbuilder", "gen-cpp", "-name", "ast"]
    cmd.extend(["-namespace", "zsp::ast", "-astdir", os.path.join(proj_dir, "ast")])
    cmd.extend(["-license", os.path.join(proj_dir, "etc", "copyright.cpp")])

    result = subprocess.run(
        cmd, 
        stderr=subprocess.STDOUT, 
        stdout=sys.stdout,
        env=env)
    if result.returncode != 0:
        raise Exception("Failed to run gen-cpp")

    cmd = [sys.executable, "-m", "astbuilder", "gen-pyext", "-name", "ast"]
    cmd.extend(["-namespace", "zsp::ast", "-astdir", os.path.join(proj_dir, "ast")])
    cmd.extend(["-package", "zuspec.fe.pss.ast", "-o", "../ext"])

    result = subprocess.run(
        cmd, 
        stderr=subprocess.STDOUT, 
        stdout=sys.stdout,
        env=env)
    if result.returncode != 0:
        raise Exception("Failed to run gen-cpp")

#		${PYTHON} -m astbuilder gen-cpp -name ast -namespace zsp::ast -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -license ${CMAKE_CURRENT_SOURCE_DIR}/etc/copyright.cpp &&
#		${PYTHON} -m astbuilder gen-pyext -name ast -namespace zsp::ast -package zsp_parser.ast -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -o ../ext

    with open("zsp_ast.d", "w") as fp:
        fp.write("\n")

    pass

if __name__ == "__main__":
    main()

