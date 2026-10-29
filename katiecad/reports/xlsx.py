# -*- coding: utf-8 -*-
"""
katiecad/reports/xlsx.py - Minimal Excel writer (.xlsx, Office Open XML) without any
third-party package (zipfile only; NO Tkinter).

Every sheet: header row (bold, filled, frozen, auto filter), column widths from the content,
integers in right-aligned columns are stored as numbers, everything else as text
(so that '001' stays '001').
"""
import re
import zipfile
from xml.sax.saxutils import escape

_UNGUELTIG = re.compile(r'[\\/*?:\[\]]')
_ZAHL = re.compile(r"^(0|-?[1-9][0-9]{0,14})$")
_XML_STEUER = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def spaltenname(i):
    """0 -> A, 25 -> Z, 26 -> AA"""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def blattname(name, vergeben):
    """Valid, unique Excel sheet name (max. 31 characters, no \\ / * ? : [ ])."""
    n = _UNGUELTIG.sub("-", str(name)).strip().strip("'") or "Sheet"
    n = n[:31]
    basis, k = n, 2
    while n.lower() in vergeben:
        suffix = " %d" % k
        n = basis[:31 - len(suffix)] + suffix
        k += 1
    vergeben.add(n.lower())
    return n


def _text(w):
    if isinstance(w, (list, tuple)):
        w = ", ".join(str(x) for x in w)
    return "" if w is None else str(w)


def _zelle(ref, wert, zahl, stil=0):
    s = ' s="%d"' % stil if stil else ""
    if wert == "":
        return '<c r="%s"%s/>' % (ref, s) if stil else ""
    if zahl and _ZAHL.match(wert):
        return '<c r="%s"%s><v>%s</v></c>' % (ref, s, wert)
    t = escape(_XML_STEUER.sub("", wert))
    return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, s, t)


def _blatt_xml(spalten, zeilen):
    """spalten: [(title, key, right_aligned)], zeilen: [dict]"""
    n = len(spalten)
    daten = [[_text(z.get(key, "")) for _t, key, _r in spalten] for z in zeilen]
    breiten = []
    for c, (titel, _k, _r) in enumerate(spalten):
        m = max([len(titel) + 2] + [max([len(p) for p in (d[c].split("\n") or [""])] or [0])
                                    for d in daten])
        breiten.append(min(max(m + 2, 8), 70))
    x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    letzte = "%s%d" % (spaltenname(max(n, 1) - 1), len(daten) + 1)
    x.append('<dimension ref="A1:%s"/>' % letzte)
    x.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
             'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    x.append('<sheetFormatPr defaultRowHeight="15"/>')
    if n:
        x.append("<cols>" + "".join(
            '<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, b)
            for i, b in enumerate(breiten)) + "</cols>")
    x.append("<sheetData>")
    x.append('<row r="1">' + "".join(
        _zelle("%s1" % spaltenname(i), t, False, 1) for i, (t, _k, _r) in enumerate(spalten))
        + "</row>")
    for r, d in enumerate(daten, start=2):
        zellen = "".join(_zelle("%s%d" % (spaltenname(i), r), d[i], spalten[i][2],
                                2 if "\n" in d[i] else 0) for i in range(n))
        x.append('<row r="%d">%s</row>' % (r, zellen))
    x.append("</sheetData>")
    if n:
        x.append('<autoFilter ref="A1:%s"/>' % letzte)
    x.append('<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>')
    x.append('<pageSetup paperSize="9" orientation="landscape" fitToHeight="0"/>')
    x.append("</worksheet>")
    return "".join(x)


_STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
           '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
           '<fills count="3"><fill><patternFill patternType="none"/></fill>'
           '<fill><patternFill patternType="gray125"/></fill>'
           '<fill><patternFill patternType="solid"><fgColor rgb="FFD9D2E9"/><bgColor indexed="64"/>'
           '</patternFill></fill></fills>'
           '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
           '<border><left/><right/><top/><bottom style="thin"><color auto="1"/></bottom><diagonal/>'
           '</border></borders>'
           '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           '<cellXfs count="3">'
           '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
           '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" '
           'applyBorder="1"/>'
           '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">'
           '<alignment wrapText="1" vertical="top"/></xf>'
           '</cellXfs>'
           '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
           '</styleSheet>')


def xlsx_schreiben(pfad, blaetter, titel="KatieCAD"):
    """blaetter: [(sheet name, [(column title, key, right_aligned)], [row dicts])].
    -> the sheet names actually used."""
    if not blaetter:
        raise ValueError("no sheets")
    vergeben, namen = set(), []
    for name, _s, _z in blaetter:
        namen.append(blattname(name, vergeben))
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>']
    for i in range(len(blaetter)):
        ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
    ct.append("</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<bookViews><workbookView/></bookViews><sheets>']
    wbrels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i, n in enumerate(namen):
        wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(n, {'"': "&quot;"}), i + 1, i + 1))
        wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1))
    wb.append("</sheets></workbook>")
    wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(namen) + 1))
    wbrels.append("</Relationships>")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>%s</dc:title>'
            '<dc:creator>KatieCAD</dc:creator></cp:coreProperties>' % escape(titel))
    with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wbrels))
        z.writestr("xl/styles.xml", _STYLES)
        for i, (_n, spalten, zeilen) in enumerate(blaetter):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), _blatt_xml(spalten, zeilen))
    return namen
