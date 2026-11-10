# Allocation and grade audit validation

Reviewed 10 November 2026. Public guideline PDF reviewed: current ETH MSc CSE guidelines,
7 October 2026 edition, especially printed pages 9–11 and 20–21. The application still uses
provisional rules and does not verify the applicability of personal regulations.

## Behaviour

- Extra electives never compensate for missing core courses, specialisation lectures or seminar,
  case studies, a project, SiP, thesis or Scientific Works.
- More than two electives are valid. **130 ECTS is a warning threshold only**: plans above it remain
  saveable and can satisfy all recorded requirements. Credits are not capped or silently dropped.
- The same module cannot count repeatedly across semesters/categories. The deliberate exception
  is Case Studies: the same number may represent the two required participations in different semesters.
- Credits already consumed by a Bachelor degree or assigned as admission requirements do not enter
  MSc totals. Scientific Works can be fulfilled at BSc level without transferring its credits.
- Planned/enrolled achievements are distinct from successful completion. Open personal admission
  requirements remain visible and prevent a claim that the recorded requirements are all complete.
- Exactly two courses occupy the core requirement. Exactly four lectures and one seminar occupy
  the specialisation requirement. Surplus courses can be reassigned to eligible electives/attend-only.
- Case Studies entries must each have three credits; a term project has eight; a thesis has thirty.
  Additional term projects belong in electives rather than inflating the term-project category.
- The manual course editor can now record seminar/lecture, field and Bachelor credit use.
- Hypothetical scenario completions do not write actual study history. Editing a real completion back
  to planned removes the stale history record. History supplies achievement status while preserving
  the scenario's chosen category and exclusion flags.
- Invalid/failing module grades, duplicated identified grade entries and wrong category counts do not
  produce a plausible-looking final grade. Seminar grades stay out of the final-grade formula.

## Coverage

The JavaScript suite contains targeted boundary cases and three independently expected matrices:

| Matrix | Cases |
| --- | ---: |
| Core × specialisation lecture × seminar × elective counts | 735 |
| Interested/planned/enrolled/completed status combinations | 256 |
| Final-grade category-count combinations | 360 |
| Total combinations | 1,351 |

Additional cases cover 120/130/above-130 boundaries, fractional credits, AML/PAI, unique manual
courses, normalized course numbers, repeated Case Studies, missing individual categories,
non-credit roles, zero/negative/non-finite credits, weight normalization, failing components versus
failing modules, repeated grade identities, BSc reuse, admission reuse and non-mutating evaluation.

Python tests exercise invalid state/import requests, numeric/type/range errors, unexpected course
statuses/categories, malformed events and semesters, duplicate record IDs, plan membership, locks,
shortlist/history metadata, nested private grade fields, storage preservation and valid draft storage.
These are storage-shape checks, not a ban on academically incomplete drafts.

The real-HTTP browser test checks visible requirement states for invalid distributions, a valid plan
above 130 ECTS, duplicate allocations, planned/completed results, escaped module titles, seminar
entry, scenario isolation and editing completed work back to planned. The existing smoke test and
real-dump HS26 timetable test remain available.

## Reproduce

No new runtime dependency is required for the app itself.

```sh
python3 -m unittest discover -s tests -v
node --test tests/study-rules.test.cjs
python3 tests/browser_smoke.py
python3 tests/browser_allocations.py
python3 tests/browser_hs26.py --database /path/to/database.sqlite
```

Node 22+ is used for developer tests only. Optional browser dependencies are pinned in
`tests/requirements.txt`; Chromium may be supplied by `CHROMIUM`, the system, or Playwright.
CI runs both Python/JavaScript suites and the synthetic browser suites without external catalogue data.

## Practical limits

Course counts and ECTS do not prove official course eligibility. Major/minor rules and recognition
require personal background and approved memberships that the app does not yet fully model.
Plans passing these numeric checks remain provisional. The 130-ECTS warning is informational and
never blocks a plan, grade selection, saving or adding courses.

See the [feature inventory and priorities](feature-inventory.md) for the remaining implementation gaps.
