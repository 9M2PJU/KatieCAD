import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
from katiecad.fileio import pdf_import as P


def pdf_bauen(inhalt, form=None, mit_layern=True):
    """Minimal PDF with two layers (L2 hidden) and a form XObject."""
    k = 0.5522847498 * 20
    objs = {}
    objs[1] = "<< /Type /Catalog /Pages 2 0 R" + (
        " /OCProperties << /OCGs [5 0 R 6 0 R] /D << /OFF [6 0 R] >> >>" if mit_layern else "") + " >>"
    objs[2] = "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    objs[3] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R "
               "/Resources << /Font << /F1 7 0 R >> /Properties << /L1 5 0 R /L2 6 0 R >> "
               "/XObject << /Fm1 8 0 R >> >> >>")
    objs[5] = "<< /Type /OCG /Name (Strom) >>"
    objs[6] = "<< /Type /OCG /Name (Hilfslinien) >>"
    objs[7] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    streams = {4: inhalt.replace("{k}", "%.4f" % k), 8: form or "0 0 m 10 10 l S"}
    out = b"%PDF-1.4\n"
    offs = {}
    for n in sorted(set(objs) | set(streams)):
        offs[n] = len(out)
        if n in streams:
            d = streams[n].encode("latin-1")
            extra = " /Type /XObject /Subtype /Form /BBox [0 0 200 200] /OC 6 0 R" if n == 8 else ""
            out += ("%d 0 obj\n<< /Length %d%s >>\nstream\n" % (n, len(d), extra)).encode() + d + b"\nendstream\nendobj\n"
        else:
            out += ("%d 0 obj\n%s\nendobj\n" % (n, objs[n])).encode()
    xr = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (max(offs) + 1)).encode()
    for n in range(1, max(offs) + 1):
        out += ("%010d 00000 n \n" % offs.get(n, 0)).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (max(offs) + 1, xr)).encode()
    return out


INHALT = """
/OC /L1 BDC 1 0 0 RG 2 w 0 0 m 100 0 l S EMC
/OC /L2 BDC 0 0 1 RG 10 10 50 20 re S EMC
/OC /L1 BDC 0 0 0 RG 100 100 m 100 {k} 100 120 m
EMC
/OC /L1 BDC 0 0 0 RG 120 100 m 120 110.4 111 120 100 120 c 89 120 80 110.4 80 100 c 80 89 89 80 100 80 c 111 80 120 89 120 100 c h S EMC
/OC /L1 BDC BT /F1 12 Tf 50 150 Td (Hallo) Tj ET EMC
/OC /L1 BDC 0.5 g 150 150 20 20 re f EMC
/OC /L1 BDC 0 0 m 30 30 l 60 0 l S EMC
q 1 0 0 1 100 0 cm /Fm1 Do Q
"""


def test_import():
    td = tempfile.mkdtemp()
    pf = os.path.join(td, "t.pdf")
    open(pf, "wb").write(pdf_bauen(INHALT))
    layers = {}
    erg = P.importiere_pdf(pf, layers)
    arten = [e.typ for e in erg.elemente]
    mm = 25.4 / 72
    assert "Strom" in layers and "Hilfslinien" in layers, layers
    assert layers["Hilfslinien"].sichtbar is False and layers["Strom"].sichtbar is True
    lin = [e for e in erg.elemente if e.typ == "linie" and e.layer == "Strom"]
    assert lin and abs(lin[0].x2 - 100 * mm) < 1e-6, lin
    rech = [e for e in erg.elemente if e.layer == "Hilfslinien"]
    assert any(e.typ == "polylinie" and e.geschlossen for e in rech), arten
    assert "kreis" in arten, arten
    k = [e for e in erg.elemente if e.typ == "kreis"][0]
    assert abs(k.r - 20 * mm) < 1e-3 and abs(k.cx - 100 * mm) < 1e-3, (k.cx, k.r)
    t = [e for e in erg.elemente if e.typ == "text"]
    assert t and t[0].inhalt == "Hallo" and t[0].layer == "Strom", t
    assert "schraffur" in arten, arten
    # form XObject: own layer (OC of the form) + shift by cm
    f = [e for e in erg.elemente if e.layer == "Hilfslinien" and e.typ == "linie"]
    assert f and abs(f[0].x1 - 100 * mm) < 1e-6, f
    assert layers["Strom"].farbe == "#ff0000" or layers["Strom"].farbe.startswith("#"), layers["Strom"].farbe


def test_ohne_layer_und_faktor():
    td = tempfile.mkdtemp()
    pf = os.path.join(td, "o.pdf")
    open(pf, "wb").write(pdf_bauen("0 0 m 72 0 l S", mit_layern=False))
    layers = {}
    erg = P.importiere_pdf(pf, layers, 1, 50.0)
    assert list(layers) == ["PDF"] or "PDF" in layers, layers
    assert abs(erg.elemente[0].x2 - 25.4 * 50) < 1e-6, erg.elemente[0].x2
    assert any("no layers" in h for h in erg.hinweise)


def test_tounicode():
    s = P.Schrift()
    s._cmap("1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
            "2 beginbfchar <0001> <0041> <0002> <00E4> endbfchar\n"
            "1 beginbfrange <0010> <0012> <0061> endbfrange")
    assert s.zwei_byte and s.dekodieren(b"\x00\x01\x00\x02\x00\x11") == "Aäb"


def test_bild():
    from PIL import Image
    from katiecad.fileio import bild_import as B
    from katiecad.model import core
    td = tempfile.mkdtemp()
    f1 = os.path.join(td, "a.png"); f2 = os.path.join(td, "b.png")
    Image.new("RGB", (40, 20), (200, 30, 30)).save(f1)
    Image.new("RGBA", (30, 30), (0, 255, 0, 128)).save(f2)
    a = B.lade_bild(f1); b = B.lade_bild(f2)
    assert a["format"] == "jpeg" and (a["pw"], a["ph"]) == (40, 20)
    assert b["format"] == "png"
    el = core.Bild(10, 20, 100, 50, **a)
    assert el.bbox() == (10, 20, 110, 70)
    el.griff_bewegen("ecke", 70, 0)
    assert abs(el.breite - 60) < 1e-9 and abs(el.hoehe - 30) < 1e-9
    el.skalieren(0, 0, 2.0)
    assert abs(el.breite - 120) < 1e-9
    d = el.to_dict(); assert d["typ"] == "bild"
    d.pop("typ"); core.Bild(**d)
    # PDF output with both image kinds, readable again by pypdf
    sp = core.PdfSeite(210, 297)
    sp.bild(10, 10, 50, 25, a["daten"], a["format"], a["pw"], a["ph"])
    sp.bild(70, 10, 30, 30, b["daten"], b["format"], b["pw"], b["ph"])
    data = core.pdf_mehrseitig([sp])
    pf = os.path.join(td, "o.pdf"); open(pf, "wb").write(data)
    from pypdf import PdfReader
    pg = PdfReader(pf).pages[0]
    xo = pg["/Resources"]["/XObject"]
    assert len(xo) == 2
    assert [im.get("/Width") for im in (xo[k].get_object() for k in xo)] == [40, 30]
    assert "/SMask" in xo["/Im2"].get_object()


def test_layer_export():
    from katiecad.model import core
    from katiecad.fileio import pdf_import as P
    td = tempfile.mkdtemp()
    sp = core.PdfSeite(210, 297)
    sp.ebene = "Wände"; sp.linie([(10, 10), (100, 10)], 0.3)
    sp.ebene = "Strom"; sp.linie([(10, 20), (100, 20)], 0.3)
    sp.text(10, 30, "Hallo", 3.5)
    sp.ebene = None; sp.linie([(10, 40), (100, 40)], 0.3)
    pf = os.path.join(td, "l.pdf"); open(pf, "wb").write(core.pdf_mehrseitig([sp]))
    from pypdf import PdfReader
    oc = PdfReader(pf).trailer["/Root"]["/OCProperties"]
    assert [o.get_object()["/Name"] for o in oc["/OCGs"]] == ["Wände", "Strom"]
    layers = {}
    erg = P.importiere_pdf(pf, layers)
    assert {"Wände", "Strom"} <= set(layers), set(layers)
    assert {e.layer for e in erg.elemente} >= {"Wände", "Strom"}


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
