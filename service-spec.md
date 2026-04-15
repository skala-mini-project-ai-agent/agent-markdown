# 서비스 명세

## 목적

이 문서는 이 저장소가 구현하려는 시스템을 "하나의 서비스" 관점에서 정의하는 기준 문서다.
`workflow.md`는 stage 흐름을, `directory.md`는 코드 배치를, 단계별 작업 문서는 구현 범위를 설명한다.
서비스 외부 인터페이스와 공통 schema 계약은 이 문서를 우선 기준으로 삼는다.

## 서비스 정의

- 서비스명: `Technology Strategy Analysis Service`
- 역할: 최신 기술 동향 수집, 주요 플레이어 식별, 품질 검증, TRL/Threat 분석, 근거 추적 가능한 전략 보고서 생성

## 서비스 경계

서비스에 포함:

- 요청 정규화
- Supervisor 기반 orchestration
- 병렬 검색, 정규화, 품질 검증
- TRL / Threat / Merge 분석
- 전략 보고서 생성
- 실행 상태 및 산출물 저장

서비스에서 제외:

- 외부 UI
- 인증/권한 시스템
- 멀티테넌트 정책
- 실제 외부 검색 API 확정

## 실행 모델

기본 실행 모델은 `비동기 job 기반 단일 파이프라인 서비스`다.

- 요청마다 `run_id`를 생성한다.
- 검색 단계는 병렬 실행하되 stage 제어는 Supervisor가 담당한다.
- 결과는 즉시 최종 보고서 대신 실행 상태와 참조값을 반환할 수 있다.
- 클라이언트는 `run_id`로 상태와 결과를 조회한다.

## 서비스 인터페이스

### 분석 요청 생성

논리 API:

- `POST /analysis-runs`

최소 요청 필드:

```json
{
  "user_query": "string",
  "technology_axes": ["HBM4", "PIM", "CXL", "Advanced Packaging", "Thermal·Power"],
  "seed_competitors": [],
  "freshness_start_year": 2024,
  "output_format": "markdown",
  "include_pdf": false
}
```

규칙:

- `seed_competitors`가 비어 있으면 `open_exploration_mode`
- `technology_axes`가 비어 있으면 기본 5개 축 사용

### 실행 상태 조회

논리 API:

- `GET /analysis-runs/{run_id}`

최소 응답 필드:

```json
{
  "run_id": "string",
  "status": "pending|running|completed|failed|revision_required",
  "current_stage": "string",
  "stage_status": {},
  "needs_review": false,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

### 결과 조회

논리 API:

- `GET /analysis-runs/{run_id}/result`

최소 응답 필드:

```json
{
  "run_id": "string",
  "quality_report_ref": "string",
  "analysis_result_ref": "string",
  "priority_matrix_ref": "string",
  "report_ref": "string",
  "approval_status": "approved|revision_required|blocked"
}
```

## 표준 상태값

상위 실행 상태:

- `pending`
- `running`
- `completed`
- `failed`
- `revision_required`

stage 상태:

- `pending`
- `in_progress`
- `passed`
- `failed`
- `skipped`
- `blocked`

## Canonical Schema 계약

### Normalized Evidence

`src/schemas/normalized_evidence_schema.py`는 최소 아래 필드를 포함해야 한다.

```json
{
  "evidence_id": "string",
  "run_id": "string",
  "agent_type": "pim|cxl|hbm4|packaging|thermal_power|indirect_signal",
  "technology": "string",
  "company": ["string"],
  "title": "string",
  "source_type": "news|press_release|paper|patent|job_posting|conference|blog|filing|other",
  "signal_type": "direct|indirect|counter_evidence",
  "source_name": "string",
  "published_at": "ISO-8601",
  "url": "string",
  "raw_content": "string",
  "key_points": ["string"],
  "signals": ["string"],
  "counter_signals": ["string"],
  "confidence": "high|medium|low",
  "quality_passed": false,
  "conflict_candidate": false,
  "unresolved": false,
  "metadata": {},
  "missing_field_flags": []
}
```

### Quality Report

`src/schemas/quality_report_schema.py`는 최소 아래 필드를 포함해야 한다.

```json
{
  "run_id": "string",
  "status": "pass|fail|warning",
  "coverage": {},
  "source_diversity": {},
  "duplicates_removed": [],
  "bias_flags": [],
  "conflict_flags": [],
  "low_evidence_cells": [],
  "low_confidence_cells": [],
  "retry_recommendations": [],
  "analysis_ready": false
}
```

### Analysis Output

`src/schemas/analysis_output_schema.py`는 최소 아래 개념을 포함해야 한다.

- `TRLAnalysisResult`
- `ThreatAnalysisResult`
- `MergedAnalysisResult`
- `PriorityMatrixRow`

### Report Output

`src/schemas/report_output_schema.py`는 최소 아래 개념을 포함해야 한다.

- `report_id`
- `run_id`
- `format`
- `sections`
- `reference_trace`
- `warnings`
- `output_path`

## 병렬 작업 소유권

### `parallel-search-implementation-plan.md`

소유 범위:

- `src/agents/base/`
- `src/agents/search/`
- `src/orchestration/parallel_search_runner.py`
- `src/normalization/`
- `src/quality/`
- `src/schemas/raw_result_schema.py`
- `src/schemas/normalized_evidence_schema.py`
- `src/schemas/quality_report_schema.py`
- `src/storage/repositories/raw_finding_repository.py`
- `src/storage/repositories/normalized_evidence_repository.py`
- `src/storage/repositories/quality_report_repository.py`
- `src/providers/search/`

### `analyze-agent.md`

소유 범위:

- `src/agents/analysis/trl_analysis_agent.py`
- `src/agents/analysis/threat_analysis_agent.py`
- `src/orchestration/merge_node.py`
- `src/schemas/analysis_output_schema.py`
- `src/storage/repositories/analysis_result_repository.py`
- `src/providers/llm/`
- `src/config/strategic_overlap.py`
- `src/prompts/analysis/trl_analysis_prompt.md`
- `src/prompts/analysis/threat_analysis_prompt.md`

### `report-agent.md`

소유 범위:

- `src/agents/analysis/report_generation_agent.py`
- `src/schemas/report_output_schema.py`
- `src/storage/repositories/report_repository.py`
- `src/prompts/analysis/report_generation_prompt.md`
- `src/config/report_sections.py`
- `src/config/report_warnings.py`

## 공통 규칙

- `normalized_evidence_schema.py`는 search 담당이 소유하지만 이 문서의 canonical 계약을 따라야 한다.
- analysis/report 담당은 필요하더라도 search schema를 독자 수정하지 않는다.
- final approval의 최종 책임자는 Supervisor다.
- 공통 계약 변경 시 `service-spec.md`와 `directory.md`를 먼저 수정한다.

## 문서 우선순위

1. `AGENTS.md`
2. `service-spec.md`
3. `workflow.md`
4. `directory.md`
5. 단계별 구현 문서
