# Three study plans from masterplan.ods

Import `all-three-study-plans.json` under **Study plans → Import / export study plans**.
Alternatively import `ods-main.json`, `ods-alternative.json` or `ods-alternative-2.json` individually.
Imports add new plans; they do not replace actual studies or existing plans.

All three contain 22 planned modules: 123 master ECTS plus 43 admission ECTS, HS 2026–FS 2029.
The main plan follows the filled spreadsheet timeline. Alternatives 1/2 are proposed completions of
its blank alternative templates, explicitly authorised by the user. Source terms/units are historical.
See ../../student-walkthrough.md for assumptions, semester workloads and fixes.

The `*-grade-assumptions.json` files are OPTIONAL separate grade-scenario imports under
**Study simulation → Import statistics / grade scenario JSON**. Select the matching study plan and
choose explicitly whether to inherit real results. These files use hypothetical numeric grades of
5.0 and assumed Pass outcomes. They contain no actual grades or observed means/standard deviations.
Save scenarios after importing. Real sigma controls require separately imported exam statistics.
