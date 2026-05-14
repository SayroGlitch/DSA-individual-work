import ctypes
import sys
import os

def load_scorer():
    if sys.platform == "win32":
        lib_name = "scorer.dll"
    elif sys.platform == "darwin":
        lib_name = "scorer.dylib"
    else:
        lib_name = "scorer.so"

    lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), lib_name)
    return ctypes.CDLL(lib_path)

scorer_lib = load_scorer()
scorer_lib.score_text.argtypes = [ctypes.c_char_p]
scorer_lib.score_text.restype  = ctypes.c_int

def score_text(text: str) -> int:
    return scorer_lib.score_text(text.encode("utf-8"))