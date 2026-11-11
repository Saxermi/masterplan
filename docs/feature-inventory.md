# MasterPlan feature inventory

Reviewed against the application and tests on 11 November 2026. “Implemented” describes the
local application on this branch; it does not imply official ETH academic recognition.

| Area | Implemented | Partial or not implemented |
| --- | --- | --- |
| Actual studies | Separate actual study record, semester allocations, shared completed history, ECTS summaries | No connection to myStudies or verified transcript import |
| Scenarios | Named plans; create, rename, duplicate, delete, switch; compare plans and semesters | No automatic optimisation or recommendation engine; scenario completions are hypothetical and do not populate real history |
| Course discovery | Local indexed VVZ dump; programme/category/specialisation/term/text filters; pagination; superseded search-response protection | First snapshot requires download; no interactive search until it is installed; no guarantee of upstream completeness |
| Eligible electives | Listed eligible MSc core programmes and CSE elective search filters | Personal approval, Bachelor credit use and official category recognition cannot be inferred reliably from catalogue membership |
| Shortlist and allocation | Shortlist courses, assign to semesters and roles, remove allocations, manual course entry/editing | Catalogue classifications remain editable provisional selections rather than official approvals |
| Degree composition | Configured category credit minima; exactly two cores; four specialisation lectures and one seminar; two or more electives; main-area credits; case studies, project, SiP, thesis and Scientific Works checks | Full regulation-version selection and individual exemptions are not implemented |
| Invalid allocations | Missing/surplus core or specialisation allocations; AML/PAI conflict; repeated module credits; Bachelor/admission reuse; wrong fixed-credit project/case/thesis records; open personal admission conditions | Complete major/minor specialisation validation depends on Bachelor background, approved field memberships and individual regulations; these are flagged for review rather than guessed |
| Extra study | More than two electives allowed; plans above 130 ECTS allowed with a warning only | No separate UI to select exactly which courses enter the degree transcript; no automatic capping or deletion of surplus credits |
| Specialisation seminar | Manual course editor records lecture/seminar and field; grade editor distinguishes seminars | Catalogue-derived seminar types and official course-to-field recognition are not automatically verified |
| Scientific Works | Successful MSc completion or the BSc completion flag; zero MSc credits | No authoritative verification or full date-based project/thesis prerequisite enforcement |
| Case Studies | Same catalogue number can count in different semesters; two three-credit participations checked | Actual attendance/presentation verification and exchange exemptions need manual confirmation |
| Projects and thesis | Credit/count checks; an extra semester project must be assigned as an eligible elective | Supervisor approval, eligibility, deadlines, permitted duration and submission workflow are not implemented |
| Timetable | Semester view, manual meetings, selectable VVZ weekly slots and exercise groups, rooms, clash highlighting | No automatic group optimisation, calendar export, room navigation or full recurrence/date-exception calendar |
| Schedule data | Local dump preferred; missing weekly times fetched from official ETH VVZ in the background and cached across restarts | Irregular/date-specific schedules require manual review; first requests wait behind the shared rate limiter |
| Course links | Official ETH links, source semester, historical proxy labels, conditional CourseReview link | No course registration or credit-request submission |
| Locks | UI guards for course/semester editing and removal | Locks are workflow controls in a local editable file, not access-control or immutable records |
| Private grades | Separate password-encrypted AES-GCM vault, component weights, final-grade category selection and formula | Grade entries are manually entered and not automatically reconciled with course allocations; no password recovery |
| Grade integrity | Missing/surplus grade categories, invalid component values/weights, failed counted modules, duplicate identified modules and AML/PAI conflict prevent a final-grade display; seminars excluded | Distinct custom names without course identifiers cannot prove two entries refer to the same real module |
| Local storage | Atomic revisioned JSON, queued browser saves, external-conflict notification/reload, import/export, separate encrypted grade file | No multi-device merge, server authentication, history/version rollback or automatic backups |
| Input integrity | Structured API/import checks for credits, status, roles, IDs, semesters, history, events and shortlist metadata; invalid input leaves stored data unchanged | Imported academic classifications are still user assertions |
| Interface | English/German, light/dark, responsive layout, PWA manifest | No complete translation of generated diagnostic text; no offline service worker or installable desktop package |
| Guidelines | Editable JSON/schema, rule provenance, configured counts/credits/exclusions/grade weights | No validated PDF extraction agent, personal applicability engine or legally binding degree audit; `sourceChecked` remains false |
| Tests | Python unit/HTTP integration suite; dependency-free JavaScript allocation/grade suite; browser smoke and invalid-allocation tests in CI; optional real-dump HS26 test | No scheduled live upstream contract monitoring, broad browser/OS matrix or full accessibility audit |

## Priority gaps

1. **Personal academic profile and recognition:** regulation applicability, Bachelor background,
   prior credit consumption, approved specialisation fields and major/minor rules, individual admission
   conditions and exemptions. These are needed before claiming an official graduation audit.
2. **Transcript selection:** a separate selection of degree-credit courses and supplementary achievements.
   Planning must continue to allow more than 130 ECTS; the existing warning never invalidates a plan.
3. **Calendar semantics:** individual dates, alternating weeks, first/second half-semester events,
   first-week room changes, academic holidays, iCalendar export and better clash analysis.
4. **Reliable data updates:** upstream schema monitoring, clearer cache freshness, comparison of old/new
   course metadata, retry visibility and an approved conflict-resolution flow for cloud-synced files.
5. **Grade-to-course reconciliation:** stable course references, recognition-aware final-grade selection,
   pass/fail achievements, imported official results and a reviewed final transcript preview.
6. **Usability and distribution:** remaining prompt-based secondary actions, a complete diagnostic
   translation catalogue, accessibility tests, packaging and a documented backup/restore workflow.

Draft planning is intentionally permissive: an incomplete course mix can be saved and explored.
The audit reports unmet requirements; it does not prevent recording a work-in-progress plan.

## Subsequent course-details/calendar update

Historical offers are selectable and movable again: missing exact offers and season mismatches
produce separate warnings, not rejection. Clickable module titles now show supplied descriptions,
learning objectives, contents and literature with DE/EN fallback. Calendar palette/time-cell click
and drag flows prefill manual meeting entry and support multiple weekly meetings per module.
The limitations concerning personal academic recognition and full date/recurrence semantics remain.

## Subsequent protected grade-simulation update

A separate Study simulation navigation item now supports named, duplicable/deletable scenarios,
study-plan selection, course-based hypothetical grades, and final-grade calculation. Real grades and
scenario entries have form-based assessment/component editing, pending-grade assumptions, target
exam calculations and additive bonuses. Simulations inherit identifiable actual marks
and assessment weights only when explicitly chosen, with read-only actual components. An unknown bonus can still be explored
as an assumption. Everything persists in the encrypted vault rather than study-plan JSON.

Still partial: official transcript import, authoritative assessment rules and rounding, automatic
recognition, and grade matching for unlinked legacy names that differ from their course titles.
The editor supports explicitly linking those records; ambiguous matches are never guessed.

## JSON analytics and flexible formulas update

Implemented: arithmetic `min`/`max` formulas shared by actual grades and simulations, configurable
additive bonus placement/grade ceiling, conservative pending-result intervals and numerical target
search; validated JSON statistics/scenario imports with preview, source data, explicit actual-grade
inheritance, mean ± deviation scenarios and selected-module adjustments. Statistics remain encrypted.
Bilingual prompts describe external PDF extraction; there is deliberately no PDF parser in the app.

Course details now contain persistent personal notes and separate term-specific advisory preparation
assessments. All-semester JSON/CSV exports link official VVZ entries; the preparation context adds
available objectives/descriptions and opt-in notes. Calendar events have minute-accurate positions,
duration and overlap lanes; repeated weekly meetings persist.

Remaining gaps: automatic PDF ingestion, authoritative exam-rule/rounding import, inferred statistics
for missing values, automatic preparation assessment generation inside the app, full recurrence/date
exceptions, and official transcript/recognition integration. Formula target search is approximate;
multiple pending assessments use a common hypothetical grade. Notes and advisory assessments are
public plan data, distinct from the encrypted grade/statistics vault.

See [the workflow](analytics-and-imports.md) for DE/EN prompts, JSON examples and screenshot reproduction.
