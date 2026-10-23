# Symbol library

Basic symbols for electrical diagrams, ready to use in KatieCAD. Open them with
**Blocks > Insert block (I)**; the library appears there as **Symbol library**
(German UI: *Symbolbibliothek*) with one sub-folder per category.

Deutsch: Grundsymbole für Stromlaufpläne. Zu finden unter **Blöcke > Block einfügen (I)**
im Eintrag **Symbolbibliothek**, je Kategorie ein Unterordner.

## Conventions

* Vertical orientation, 5 mm pole pitch, pins at +-7.5 mm (two-pin symbols).
* Every device symbol carries **one electrical mask** (IND / TYP / PER).
  Coils, motors, fuses, breakers, lamps etc. are *main devices*;
  contacts, push buttons and switches that belong to a coil or a control element are
  *auxiliary devices* (role "Hilfsgerät"), so that they refer to the main device with the
  same IND (e.g. coil `K1` and its contacts `K1`). Change the role with **Edit attributes** if needed.
* Pin numbering follows the usual contact designations (13/14 NO, 21/22 NC, 11/12/14 changeover,
  1..6 main contacts, A1/A2 coils, 95/96 overload contact).
* Line weight 0.35 mm, text height 2 mm.
* Placeholder values (`IND`, `TYP`, `PER`) are treated as "not filled in" by the lists.

## Symbols

### 01 Connections

| Name | Deutsch | Pins |
|---|---|---|
| Earth | Erde | PE |
| Chassis | Masse / Gehäuse | M |

### 02 Contacts and switches

| Name | Deutsch | Pins |
|---|---|---|
| NO contact | Schließer | 13, 14 |
| NC contact | Öffner | 21, 22 |
| Changeover contact | Wechsler | 11, 12, 14 |
| NO contact 3-pole | Schließer 3-polig (Hauptkontakte) | 1, 2, 3, 4, 5, 6 |
| NO contact 4-pole | Schließer 4-polig | 1, 2, 3, 4, 5, 6, 7, 8 |
| Push button NO | Taster, Schließer | 13, 14 |
| Push button NC | Taster, Öffner | 21, 22 |
| Switch NO | Schalter (handbetätigt), Schließer | 13, 14 |
| Main switch 3-pole | Hauptschalter 3-polig (handbetätigt) | 1, 2, 3, 4, 5, 6 |

### 03 Protection

| Name | Deutsch | Pins |
|---|---|---|
| Fuse 1-pole | Sicherung 1-polig | 1, 2 |
| Fuse 2-pole | Sicherung 2-polig | 1, 2, 3, 4 |
| Fuse 3-pole | Sicherung 3-polig | 1, 2, 3, 4, 5, 6 |
| Fuse 4-pole | Sicherung 4-polig | 1, 2, 3, 4, 5, 6, 7, 8 |
| Circuit breaker 1-pole | Leitungsschutzschalter / Leistungsschalter 1-polig | 1, 2 |
| Circuit breaker 3-pole | Leistungsschalter 3-polig | 1, 2, 3, 4, 5, 6 |
| Motor protection switch 3-pole | Motorschutzschalter 3-polig | 1, 2, 3, 4, 5, 6 |
| Overload relay 3-pole | Motorrelais / Überstromauslöser 3-polig (Hauptstrompfad) | 1, 2, 3, 4, 5, 6 |
| Overload relay contact NC | Motorrelais Öffnerkontakt (95/96) | 95, 96 |

### 04 Coils and actuators

| Name | Deutsch | Pins |
|---|---|---|
| Coil | Spule (Schütz / Relais) | A1, A2 |
| Solenoid valve coil | Magnetventil (Spule) | 1, 2 |
| Indicator lamp | Meldeleuchte | X1, X2 |
| Horn / buzzer | Hupe / Summer | 1, 2 |

### 05 Motors and drives

| Name | Deutsch | Pins |
|---|---|---|
| Motor 3-phase | Drehstrommotor | U1, V1, W1 |
| Motor 1-phase | Wechselstrommotor | U1, U2 |
| Motor DC | Gleichstrommotor | A1, A2 |

### 06 Passive components

| Name | Deutsch | Pins |
|---|---|---|
| Resistor | Widerstand | 1, 2 |
| Capacitor | Kondensator | 1, 2 |
| Capacitor polarised | Elektrolytkondensator (gepolt) | 1, 2 |
| Inductor | Spule / Drossel | 1, 2 |

### 07 Semiconductors

| Name | Deutsch | Pins |
|---|---|---|
| Diode | Diode | A, K |
| Zener diode | Z-Diode | A, K |
| LED | Leuchtdiode | A, K |
| Bridge rectifier | Brückengleichrichter | +, -, AC1, AC2 |

### 08 Sources and transformers

| Name | Deutsch | Pins |
|---|---|---|
| Battery | Batterie | +, - |
| Power supply AC-DC | Netzteil AC/DC | L, N, +, - |
| Transformer 1-phase | Transformator einphasig | 1, 2, 3, 4 |

### 09 Measuring

| Name | Deutsch | Pins |
|---|---|---|
| Voltmeter | Voltmeter | 1, 2 |
| Ammeter | Amperemeter | 1, 2 |

## Notes

* The symbols are **simplified drawings in the spirit of IEC 60617 / DIN EN 60617**,
  drawn from scratch for this project. They are not a copy of the standard. Please check
  them against the standard (and your company rules) before using them in released drawings;
  corrections are welcome.
* Actuator heads of push buttons and hand-operated switches, the thermal release of the motor
  protection switch and the overload relay are particularly simplified.
* **Regenerate / extend:** the files are produced by `tools/make_symbols.py`. Add a symbol
  there (a few lines of drawing code) and run `python tools/make_symbols.py`. Hand-made blocks
  can simply be placed in any sub-folder of `symbols/` as `*.katieblock` files
  (**Blocks > Save block as file...**), but regenerating deletes the category sub-folders first,
  so keep your own symbols in your own block folder or add them to the script.
