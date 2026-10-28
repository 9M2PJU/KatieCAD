"""Runs all tests one after another:  python tests/run_all.py"""
import subprocess, sys, os
hier = os.path.dirname(os.path.abspath(__file__))
tests = ["test_logic", "test_app", "test_app2", "test_electrical_basics",
         "test_electrical_symbols", "test_electrical_devices", "test_titleblock",
         "test_grid", "test_autowire", "test_blockbrowser", "test_kabel", "test_reports", "test_symbols", "test_pruefung", "test_pdf_import", "test_suchen", "test_cad2d", "test_listen", "test_funktion", "test_aendern", "test_3d"]
fehler = 0
for t in tests:
    r = subprocess.run([sys.executable, os.path.join(hier, t + ".py")],
                       capture_output=True, text=True)
    zeile = (r.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1]
    print(("OK    " if r.returncode == 0 else "FEHLER"), t, "-", zeile)
    fehler += r.returncode != 0
sys.exit(1 if fehler else 0)
