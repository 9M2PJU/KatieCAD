import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)
import types, ast, symtable, builtins
import importlib
mods = ["katiecad.model.core", "katiecad.common.i18n", "katiecad.model.project",
        "katiecad.model.blocks", "katiecad.ui.widgets", "katiecad.ui.dialogs",
        "katiecad.electrical.logic", "katiecad.ui.sidebar", "katiecad.fileio.pdf",
        "katiecad.common.config", "katiecad.ui.app"]
loaded = {m: importlib.import_module(m) for m in mods}
print("Imports OK")

problems = 0
for name, mod in loaded.items():
    src = open(mod.__file__, encoding="utf-8").read()
    top = symtable.symtable(src, mod.__file__, "exec")
    defined = set(dir(mod)) | set(dir(builtins))
    def walk(t):
        global problems
        for sym in t.get_symbols():
            if t.get_type() == "function" and sym.is_global() and sym.is_referenced():
                if sym.get_name() not in defined:
                    print(f"[{name}] undefined global '{sym.get_name()}' in {t.get_name()}")
                    problems += 1
        for c in t.get_children():
            walk(c)
    walk(top)

# check self.<attr> for CadApp and sidebar
def attr_check(modname, clsname):
    global problems
    src = open(loaded[modname].__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == clsname)
    assigned, used = set(), {}
    for n in ast.walk(cls):
        if isinstance(n, ast.FunctionDef):
            assigned.add(n.name)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self":
            if isinstance(n.ctx, ast.Store):
                assigned.add(n.attr)
            else:
                used.setdefault(n.attr, n.lineno)
    base = getattr(loaded[modname], clsname)
    for a, ln in sorted(used.items(), key=lambda x: x[1]):
        if a not in assigned and not hasattr(base, a):
            print(f"[{modname}] self.{a} nie definiert (Zeile {ln})")
            problems += 1
attr_check("katiecad.ui.app", "CadApp")
attr_check("katiecad.ui.sidebar", "Seitenleiste")
print("Probleme:", problems)
