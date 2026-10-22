"""Tkinter-Attrappe, damit die Logik ohne Display getestet werden kann."""
import sys, types, ast, symtable, builtins

class _Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Any()
    def __call__(self, *a, **k): return _Any()

def mk(name):
    m = types.ModuleType(name)
    m.__getattr__ = lambda n: type(n, (_Any,), {})
    return m

tk = mk("tkinter")
for sub in ("ttk", "filedialog", "messagebox", "colorchooser", "simpledialog", "font"):
    mod = mk("tkinter." + sub)
    sys.modules["tkinter." + sub] = mod
    setattr(tk, sub, mod)
sys.modules["tkinter"] = tk

