flowchart TD
    U([User Query])
    S[Supervisor]
    SE[Search Agents]
    QG[Quality Gate Node]
    TRL[TRL Analysis Agent]
    THR[Threat Analysis Agent]
    RP[Report Generation Agent]
    END([END])

    U --> S

    S -->|지시시| SE
    S -->|검증 요청| QG
    S -->|분석 지시| TRL
    S -->|분석 지시| THR
    S -->|보고서 생성| RP
    S --> END

    SE -->|수집 완료| S
    QG -->|pass or fail | S
    TRL -->|TRL 매트릭스| S
    THR -->|위협 수준| S
    RP -->|보고서 완료| S

