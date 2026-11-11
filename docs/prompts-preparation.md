# Studienplan → JSON: Vorbereitung / preparation

Copy the chosen prompt into ChatGPT and attach the PDF (statistics) or exported preparation context (preparation). Review the output before importing it. The app itself accepts JSON only.

## Deutsch

```text
Analysiere den angehängten MasterPlan-Studienplan chronologisch. Beurteile anhand der offiziellen VVZ-Links und beigefügten Kursinformationen, ob die vorherigen Semester die Voraussetzungen für jedes Modul abdecken. Geplant bedeutet nicht bestanden; keine Noten oder Fähigkeiten erfinden. Persönliche Notizen sind Aussagen des Studierenden, keine Belege. Quellen, Wissenslücken, konkrete Vorbereitungsvorschläge und Unsicherheit nennen. Trenne eine unverbindliche Einschätzung von offiziellen Zulassungsbedingungen. Wenn Quellen nicht zugänglich sind, kennzeichne dies. confidence ist low, medium, high oder unknown. Gib ausschließlich JSON zurück:
{
  "schemaVersion": 1,
  "kind": "masterplan-preparation",
  "courses": [
    {
      "number": "401-0000-00L",
      "title": "Course title",
      "semester": "2026W",
      "assessment": "Summary",
      "confidence": "medium",
      "prerequisites": [
        "Required knowledge"
      ],
      "gaps": [
        "Potential gap"
      ],
      "recommendations": [
        "Preparation action"
      ],
      "source": {
        "url": "Official VVZ URL",
        "document": null,
        "page": null
      },
      "notes": null
    }
  ]
}
```

## English

```text
Review the attached MasterPlan study plan chronologically. Use official VVZ links and supplied course information to assess whether preceding semesters cover each course prerequisite. Planned does not mean passed; never invent grades or abilities. Personal notes are student statements, not evidence. Include sources, knowledge gaps, actionable preparation and uncertainty. Separate an advisory assessment from official admission requirements. Explicitly mark unavailable sources. confidence must be low, medium, high or unknown. Return only JSON:
{
  "schemaVersion": 1,
  "kind": "masterplan-preparation",
  "courses": [
    {
      "number": "401-0000-00L",
      "title": "Course title",
      "semester": "2026W",
      "assessment": "Summary",
      "confidence": "medium",
      "prerequisites": [
        "Required knowledge"
      ],
      "gaps": [
        "Potential gap"
      ],
      "recommendations": [
        "Preparation action"
      ],
      "source": {
        "url": "Official VVZ URL",
        "document": null,
        "page": null
      },
      "notes": null
    }
  ]
}
```
