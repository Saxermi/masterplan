# Student-style walkthrough: three plans from masterplan.ods

The uploaded spreadsheet was treated as planning data, not as instructions or an executable file.
Its leftmost main timeline is filled. The two alternative timelines contain the six admission
requirements and otherwise mostly blank placeholders. The user explicitly chose to have those
alternatives completed as proposals using the spreadsheet's course list.

## Import files

Download [the complete import pack](examples/ods-scenarios/masterplan-import-pack.zip), or load
[all three study plans](examples/ods-scenarios/all-three-study-plans.json) under **Study plans →
Import / export study plans**. Preview, then **Import as new plans**. The actual record, shared
history and existing plans are retained. Repeated imports receive new IDs and distinct names.

Individual plans:

- [Main plan](examples/ods-scenarios/ods-main.json)
- [Physics-first proposal](examples/ods-scenarios/ods-alternative.json)
- [Astrophysics proposal](examples/ods-scenarios/ods-alternative-2.json)

Each has 22 modules, 123 planned master ECTS and 43 separate admission ECTS. All courses are marked
**planned**, including Scientific Works. No achieved grades or completed work have been invented.

| Semester | Main | Physics first | Astrophysics focus |
| --- | ---: | ---: | ---: |
| HS 2026 | 26 | 26 | 26 |
| FS 2027 | 26 | 26 | 31 |
| HS 2027 | 29 | 33 | 20 |
| FS 2028 | 28 | 27 | 32 |
| HS 2028 | 27 | 24 | 27 |
| FS 2029 | 30 | 30 | 30 |

These are workload totals, including admission courses. The 43 admission ECTS do not count towards
the 123 master ECTS. Physics first moves the ungraded seminar/Scientific Works earlier and the second
Case Studies participation to FS 2028. Astrophysics focus replaces General Relativity with
Astrophysics II, moves Computational Statistics to FS 2027, moves the seminar/Scientific Works earlier,
and schedules Case Studies in FS/HS 2028. It preserves the same master-credit total.

Optional **illustrative grade scenarios** can be imported separately under **Study simulation →
Import statistics / grade scenario JSON**, selecting the corresponding study plan and explicitly
choosing whether to inherit actual results:

- [Main grade assumptions](examples/ods-scenarios/ods-main-grade-assumptions.json)
- [Physics-first grade assumptions](examples/ods-scenarios/ods-alternative-grade-assumptions.json)
- [Astrophysics grade assumptions](examples/ods-scenarios/ods-alternative-2-grade-assumptions.json)

These examples assume **5.0 for numeric courses and Pass for pass/fail courses**. They are examples,
not actual results, extracted exam statistics or predictions from the spreadsheet. The spreadsheet
contains no exam means or deviations; none were fabricated for the deliverables. Import real
statistics separately to enable sigma controls. The browser regression uses explicitly synthetic
mean/deviation values to exercise those controls.

## Walkthrough and issues fixed

The real browser imported all three plans, inspected the semester allocations, exported each plan
and the combined bundle, created three linked grade scenarios, exercised every available numeric
course's sigma buttons (54 adjustments), set the 12 pass/fail outcomes, saved and reloaded them,
entered a real pass/fail record in the grade editor, and imported the delivered illustrative grade file (including its P/F outcomes). It then reran after the fixes below.

| Issue / inconvenience | Fix and verification |
| --- | --- |
| Ungraded courses had numeric assumption fields and could receive a fallback grade. | Added explicit numeric/pass-fail assessment modes, outcome selectors and no numeric fallback or sigma for P/F. Defaults for Case Studies, Scientific Works and specialisation seminars are editable. |
| An ungraded result could be mistaken for a missing/zero grade or a numeric contribution. | Pass/Fail/Pending display separately; P/F receives no numerical weight. Credits/category counts remain. Pending/failed P/F achievements have a completion notice beside the grade average. |
| Sigma adjustment required the global form and module checkbox list. | Each available numerical course now has −1σ / mean / +1σ buttons and an individual-factor indicator. |
| Global changes could undo the purpose of an individual sigma choice. | Individual factors are pinned and saved independently; global updates preserve them. Each course can return to the global setting. |
| After setting many individual factors, returning to global control required repetitive per-row actions. | Added **Reset individual σ settings to global**, preserving manual numeric overrides and actual results. |
| A pending P/F selection was not included by the existing Save scenarios flow. | Pending outcome selections are now tracked, survive rerenders and are committed by Save, like pending numeric edits. Verified after reload. |
| The numeric-missing filter did not help locate unresolved ungraded outcomes. | Added a separate pending P/F filter and pending-outcome counts; the P/F filter includes inherited real outcomes too. |
| The existing plan JSON export was descriptive rather than fully importable. | It now preserves empty semesters, locks, assessment mode, category, admission/Bachelor metadata, source unit/term and meetings. Added single/bundle import with preview and fresh IDs. |
| Some official course titles contain the old source semester, which was confusing beside a future target term in the grade overview. | The overview now also shows historical-reference warnings and links the exact source VVZ unit. |
| The preview did not explain why a plan's workload exceeded its master-credit total. | Added separate master/admission ECTS totals before import. |
| Admission/project courses opened in grade details with a misleading default Core dropdown. | Non-averaged categories now display Exclude from final grade while retaining the original course category. |
| Existing graded seminar records could be misclassified by new P/F defaults. | Explicit assessment mode wins; legacy recorded numeric marks and partial results remain numeric until deliberately reclassified. |
| A typo in an imported meeting date could pass preview but be rejected by the server. | Impossible ISO dates are rejected in preview; reversed times and malformed course/plan data also fail before import. |

## Source ambiguities and assumptions (not application bugs)

- The spreadsheet's generic Case Studies code differs from the linked semester-specific VVZ units.
  Import files use the linked unit's actual number from the local VVZ snapshot. Different semesters
  remain separate participations.
- Spreadsheet labels `V`, `S`, `A` and `D` denote teaching/assessment types, not the stable unit-number
  suffix. Numbers/titles were normalised using the linked unit, not guessed from those labels.
- “Philosophy of War / or Swedish course” is resolved to the explicitly linked Philosophy of War.
- Ungraded presentation and Scientific Works are P/F. Case Studies attendance/presentation is modelled
  as P/F; confirm the applicable assessment rules. The semester project and other explicitly graded
  courses remain numeric. Assessment mode can be changed in the course editor.
- All offerings are historical 2025/2026 references for target semesters through 2029. Source links
  are preserved and never presented as confirmed future offerings. Verify future availability,
  recognition/Bachelor reuse, admission-letter requirements and prerequisites before enrolment.
- Scientific Works remains planned, so its completion-dependent checks remain pending. A grade
  simulation is not proof of completed degree requirements. The >130 master-ECTS limit stays a warning.

## Reproduce

```sh
node --test tests/*.test.cjs
python -m unittest discover -s tests -v
SCREENSHOT_DIR=docs/screenshots python tests/browser_student_walkthrough.py
```

The browser uses a temporary personal folder. It does not overwrite the user's study or grade files.
The raw uploaded spreadsheet and its personal comments are not committed to the repository.
