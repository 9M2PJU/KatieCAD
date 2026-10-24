# Title block templates

Every `*.cadjson` drawing in this folder (and in a `title_blocks` folder inside a
project folder) appears in **Insert > Frame + title block**.

How to make your own:

1. Draw the title block in the **model** of a normal KatieCAD drawing.
2. The drawing's origin `(0, 0)` is the **lower right corner of the sheet frame**.
   The title block therefore extends to the left (x < 0) and upwards (y > 0).
   Units are millimetres.
3. For fillable fields use attribute definitions (ATTDEF). These tags are filled in
   automatically and stay up to date:

   | Tag | Content |
   |---|---|
   | `PAGE` | sheet number in the project |
   | `PAGES` | number of sheets |
   | `SHEET` | sheet name |
   | `PROJECT` | project name |
   | `DATE` | today |
   | `SCALE` | scale of the first viewport |
   | `FORMAT` | paper format (e.g. A3) |

   Also filled in automatically on every sheet, from **Project > Project properties**
   (use whichever spelling suits your template; an empty project value clears the
   field, without a project nothing is touched):

   | Tag (German / English) | Content |
   |---|---|
   | `GEZEICHNET` / `DRAWN`, `GEZEICHNET_DATUM` / `DRAWN_DATE` | drawn by (+ date, default today) |
   | `GEPRUEFT` / `VERIFIED`, `GEPRUEFT_DATUM` / `VERIFIED_DATE` | checked by (+ date) |
   | `ZEICHNUNGSNUMMER` / `DRAWINGNUMBER` | drawing number |
   | `FIRMA` / `COMPANY`, `KUNDE` / `CUSTOMER`, `AUFTRAG` / `ORDER`, `ANLAGE` / `PLANT`, `REVISION` | project data |
   | `FORMAT`, `BLATTFORMAT`, `PAPIERFORMAT`, `SIZE` | paper format of the layout, e.g. `A0` |
   | `TITLE` / `TITEL` | customer - project name - sheet name |
   | `TITEL1`, `TITEL2`, `TITEL3` (`TITLE1`..`3`) | the three parts alone: customer, project name, sheet name |
   | `REV1_STAND`, `REV1_AENDERUNG`, `REV1_NAME`, `REV1_DATUM` (English: `REV1_INDEX`, `REV1_CHANGE`, `REV1_NAME`, `REV1_DATE`) | revision table, rows `REV1` to `REV4` |

   Spelling is tolerant: case, underscores, hyphens and umlauts do not matter
   (`Geprüft_Datum` = `GEPRUEFT_DATUM`), and the revision fields are also found as
   `STAND1`, `AENDERUNG1`, `NAME1`, `DATUM1` (row 1 to 4). The checked-by date
   `GEPRUEFT_DATUM` is filled from **Project properties** as well.

   All other tags are asked for when the title block is inserted and can be changed
   later with the attribute editor.
4. Save the drawing here, or use **Insert > Save drawing as title block template**.

The frame has a 20 mm margin on the left and 5 mm on the other sides.
On A4 the punched margin is at the top: 5 mm left, 15 mm top, 5 mm right and bottom.
Inserting a title block again replaces the existing one.
`Example_A3.cadjson` shows how a template is built.
