"""Runs all tests one after another:  python tests/alle_tests.py"""
import subprocess, sys, os
hier = os.path.dirname(os.path.abspath(__file__))
tests = ["test_logic", "test_app", "test_app2", "test_electrical_basics",
         "test_electrical_symbols", "test_electrical_devices"]
fehler = 0
for t in tests:
    r = subprocess.run([sys.executable, os.path.join(hier, t + ".py")],
                       capture_output=True, text=True)
    zeile = (r.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1]
    print(("OK    " if r.returncode == 0 else "FEHLER"), t, "-", zeile)
    fehler += r.returncode != 0
sys.exit(1 if fehler else 0)
