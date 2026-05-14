import subprocess
import sys

def build():
    if sys.platform == "win32":
        out = "scorer.dll"
    elif sys.platform == "darwin":
        out = "scorer.dylib"
    else:
        out = "scorer.so"

    cmd = ["gcc", "-shared", "-o", out, "-fPIC", "scorer.c"]
    print(f"Compiling scorer.c → {out}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Build failed:")
        print(result.stderr)
        sys.exit(1)
    else:
        print(f"Build successful → {out}")

if __name__ == "__main__":
    build()