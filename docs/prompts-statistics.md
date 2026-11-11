# PDF → JSON: Prüfungsstatistiken / exam statistics

Copy the chosen prompt into ChatGPT and attach the PDF (statistics) or exported preparation context (preparation). Review the output before importing it. The app itself accepts JSON only.

## Deutsch

```text
Lies das beigefügte PDF mit Prüfungsstatistiken. Extrahiere für jedes Modul Kursnummer, Titel, Prüfungssemester, Durchschnittsnote, Anzahl bewerteter Studierender und Standardabweichung. Unterscheide Teilnehmerzahl von bestandenen Prüfungen. Fehlende oder unlesbare Werte sind null; nichts schätzen, keine Standardabweichung aus dem Durchschnitt ableiten. Quellen mit Dokument und Seite erhalten, unterschiedliche Prüfungssemester als getrennte Einträge führen. semester ist YYYY[S/W], z. B. 2026S für FS 2026 oder 2026W für HS 2026; wenn die Zuordnung zum Vorlesungssemester unklar ist, null. Titel nicht in Kursnummern umdeuten. Notenskala 1–6, Standardabweichung nicht mit Standardfehler verwechseln. Gib ausschließlich valides JSON nach diesem Beispiel aus:
{
  "schemaVersion": 1,
  "kind": "masterplan-statistics",
  "name": "Exam statistics",
  "courses": [
    {
      "number": "401-0000-00L",
      "title": "Course title",
      "semester": "2026W",
      "mean": 4.5,
      "sampleSize": 120,
      "stddev": 0.7,
      "source": {
        "document": "Document name",
        "page": 3,
        "url": null
      },
      "notes": null
    }
  ]
}
```

## English

```text
Read the attached PDF of exam statistics. Extract course number, title, examination semester, mean grade, number of graded students and standard deviation for each course. Distinguish student counts from passed exams. Use null for absent/illegible values; never invent values or infer deviation from the mean. Preserve document/page provenance and separate examination terms. semester uses YYYY[S/W], e.g. 2026S for spring or 2026W for autumn; use null if the lecture-term mapping is unclear. Never invent a course number from a title. Grades use the 1–6 scale; do not confuse standard error and standard deviation. Return only valid JSON following this example:
{
  "schemaVersion": 1,
  "kind": "masterplan-statistics",
  "name": "Exam statistics",
  "courses": [
    {
      "number": "401-0000-00L",
      "title": "Course title",
      "semester": "2026W",
      "mean": 4.5,
      "sampleSize": 120,
      "stddev": 0.7,
      "source": {
        "document": "Document name",
        "page": 3,
        "url": null
      },
      "notes": null
    }
  ]
}
```
