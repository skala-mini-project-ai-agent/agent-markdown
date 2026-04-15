# 디렉터리 구조 정의

## 목적

이 문서는 `workflow.md`의 요구사항을 실제 구현 구조로 옮기기 위한 디렉터리 설계안이다.
특히 현재 우선 구현 대상인 아래 단계를 중심으로 작성한다.

- 3. 병렬 검색 단계
- 4. 검색 결과 정규화 및 적재 단계
- 5. 전역 품질 검증 단계

다만 이후 6~11단계까지 자연스럽게 확장할 수 있도록 전체 워크플로우 기준으로 구조를 잡는다.

## 설계 원칙

- `workflow.md`의 stage 경계를 코드 구조에 반영한다.
- Agent, Node, Supervisor 책임을 디렉터리 수준에서 분리한다.
- 병렬 검색 결과와 정규화 결과를 분리 저장한다.
- 품질 검증 결과는 사람용 문서보다 후속 stage가 읽기 쉬운 구조를 우선한다.
- 외부 검색 provider, 저장소, LLM 판정기는 인터페이스로 분리한다.
- targeted retry가 가능하도록 실행 상태와 품질 리포트를 별도 관리한다.

## 권장 디렉터리 구조

```text
agent-project/
  AGENTS.md
  service-spec.md
  workflow.md
  directory.md
  parallel-search-implementation-plan.md
  analyze-agent.md
  report-agent.md
  supervisor.md
  src/
    app/
      bootstrap.py
      pipeline.py
    supervisor/
      supervisor.py
      planning.py
      retry_controller.py
      stage_gate.py
    agents/
      base/
        base_agent.py
        base_search_agent.py
      search/
        pim_search_agent.py
        cxl_search_agent.py
        hbm4_search_agent.py
        packaging_interconnect_agent.py
        thermal_power_agent.py
        indirect_signal_patent_agent.py
      analysis/
        trl_analysis_agent.py
        threat_analysis_agent.py
        report_generation_agent.py
    orchestration/
      parallel_search_runner.py
      stage_executor.py
      execution_context.py
      merge_node.py
    normalization/
      evidence_normalizer.py
      evidence_loader.py
      tagging.py
      keypoint_extractor.py
    quality/
      quality_gate.py
      coverage_matrix.py
      source_diversity.py
      deduplication.py
      bias_detection.py
      conflict_detection.py
      confidence_evaluator.py
    schemas/
      query_schema.py
      raw_result_schema.py
      normalized_evidence_schema.py
      quality_report_schema.py
      analysis_output_schema.py
      report_output_schema.py
      supervisor_state_schema.py
    storage/
      repositories/
        raw_finding_repository.py
        normalized_evidence_repository.py
        quality_report_repository.py
        execution_state_repository.py
        analysis_result_repository.py
        report_repository.py
      adapters/
        jsonl_adapter.py
        sqlite_adapter.py
    providers/
      search/
        base_search_provider.py
        web_search_provider.py
        patent_search_provider.py
        conference_signal_provider.py
      llm/
        base_llm_provider.py
        llm_judge_provider.py
    config/
      settings.py
      thresholds.py
      source_weights.py
      agent_queries.py
      strategic_overlap.py
      report_sections.py
      report_warnings.py
    prompts/
      search/
        pim_search_prompt.md
        cxl_search_prompt.md
        hbm4_search_prompt.md
        packaging_interconnect_prompt.md
        thermal_power_prompt.md
        indirect_signal_patent_prompt.md
      normalization/
        keypoint_extraction_prompt.md
      quality/
        llm_quality_judge_prompt.md
      analysis/
        trl_analysis_prompt.md
        threat_analysis_prompt.md
        conflict_resolution_prompt.md
        report_generation_prompt.md
    utils/
      dates.py
      text.py
      ids.py
      logging.py
    models/
      enums.py
      constants.py
  data/
    raw/
      search_runs/
    normalized/
      evidence_sets/
    quality/
      reports/
    analysis/
      trl/
      threat/
      reports/
  tests/
    fixtures/
      raw_findings/
      normalized_evidence/
      quality_reports/
    unit/
      test_parallel_search_runner.py
      test_evidence_normalizer.py
      test_quality_gate.py
      test_retry_controller.py
    integration/
      test_search_to_quality_pipeline.py
  scripts/
    run_pipeline.py
    run_parallel_search.py
    run_quality_gate.py
```

## 최상위 문서 역할

- `AGENTS.md`: 프로젝트 목표와 작업 원칙 정의
- `service-spec.md`: 서비스 요청/응답, 실행 모델, 공통 schema, 병렬 작업 ownership 기준
- `workflow.md`: stage별 요구사항과 제어 전략 정의
- `directory.md`: 디렉터리 구조와 모듈 책임 정의
- `parallel-search-implementation-plan.md`: 3~5단계 구현 계획과 search/normalization/quality 소유 범위
- `analyze-agent.md`: 7~9단계 구현 계획과 analysis/merge 소유 범위
- `report-agent.md`: 10단계 구현 계획과 report 소유 범위
- `supervisor.md`: stage gate, retry, approval 제어 구현 계획

## Canonical 계약

서비스 수준의 canonical 계약은 `service-spec.md`를 따른다.

- 요청/응답 모델은 `service-spec.md`의 서비스 인터페이스를 기준으로 한다.
- `src/schemas/normalized_evidence_schema.py`는 분석과 보고서가 공통으로 소비하는 고정 계약이다.
- `src/schemas/analysis_output_schema.py`는 분석 단계 담당이 소유한다.
- `src/schemas/report_output_schema.py`는 보고서 단계 담당이 소유한다.
- final approval의 최종 책임자는 `Supervisor`다.

## 병렬 작업 기준

`parallel-search-implementation-plan.md`, `analyze-agent.md`, `report-agent.md`는 동시에 구현할 수 있도록 책임을 분리한다.

- Search/Normalization/Quality 담당은 `src/agents/search`, `src/normalization`, `src/quality`, search 관련 schema만 수정한다.
- Analysis 담당은 `src/agents/analysis` 중 `trl_analysis_agent.py`, `threat_analysis_agent.py`, `src/orchestration/merge_node.py`, `analysis_output_schema.py`만 수정한다.
- Report 담당은 `report_generation_agent.py`, `report_output_schema.py`, `report_repository.py`, report 관련 config/prompt만 수정한다.
- 공통 계약 변경은 `service-spec.md`와 이 문서를 먼저 수정한 뒤 각 작업 문서에 반영한다.

## 디렉터리별 책임

### `src/app`

애플리케이션 진입점과 전체 파이프라인 조립 책임을 가진다.

- `bootstrap.py`: 설정, provider, repository 초기화
- `pipeline.py`: stage 순서를 조립하고 실행

### `src/supervisor`

`workflow.md`의 2단계와 6단계의 중앙 통제 책임을 담당한다.

- `supervisor.py`: stage 승인과 전체 흐름 제어
- `planning.py`: 초기 실행 계획 및 query bundle 생성
- `retry_controller.py`: targeted retry 대상 계산
- `stage_gate.py`: 단계별 pass/fail gate 관리

### `src/agents`

Agent 구현을 모아 둔다.

- `base/`: 공통 Agent 인터페이스
- `search/`: 3단계 병렬 검색 Agent
- `analysis/`: 7단계 이후 분석 및 보고서 Agent

병렬 구현 기준:

- search 담당: `base/`, `search/`
- analysis 담당: `analysis/trl_analysis_agent.py`, `analysis/threat_analysis_agent.py`
- report 담당: `analysis/report_generation_agent.py`

### `src/orchestration`

여러 Agent와 Node를 실제로 실행하는 조정 계층이다.

- `parallel_search_runner.py`: 6개 Search Agent 병렬 실행
- `stage_executor.py`: stage 단위 실행 추상화
- `execution_context.py`: run_id, mode, retry_count 같은 실행 메타데이터 관리
- `merge_node.py`: analysis 결과 deterministic merge

### `src/normalization`

`workflow.md` 4단계 전담 디렉터리다.

- `evidence_normalizer.py`: raw findings를 공통 schema로 변환
- `evidence_loader.py`: 정규화 결과 적재
- `tagging.py`: source/date/company/technology 태깅
- `keypoint_extractor.py`: raw_content와 key_points 분리 로직

### `src/quality`

`workflow.md` 5단계 전담 디렉터리다.

- `quality_gate.py`: 최종 품질 판정 엔트리 포인트
- `coverage_matrix.py`: technology x company coverage 계산
- `source_diversity.py`: 출처 유형 다양성 검사
- `deduplication.py`: 중복/재인용 제거
- `bias_detection.py`: 기업 발표 편향 탐지
- `conflict_detection.py`: 상충 evidence 식별
- `confidence_evaluator.py`: low confidence 비율 판정

### `src/schemas`

stage 간 계약을 고정하는 schema 모듈이다.

- `query_schema.py`: Agent 입력 query bundle 구조
- `raw_result_schema.py`: Agent raw output 구조
- `normalized_evidence_schema.py`: 후속 분석과 보고서 공통 evidence 구조
- `quality_report_schema.py`: 품질 검증 결과 구조
- `analysis_output_schema.py`: 7단계 이후 분석 결과 구조
- `report_output_schema.py`: 10단계 보고서 결과 구조
- `supervisor_state_schema.py`: 실행 상태와 stage gate 결과 구조

### `src/storage`

데이터 저장소 접근을 추상화한다.

- `repositories/`: 도메인별 저장 인터페이스
- `adapters/`: JSONL, SQLite 같은 실제 저장 방식

이 구조를 두는 이유는 초기에는 파일 저장으로 시작하더라도 이후 DB로 바꿀 수 있게 하기 위함이다.

### `src/providers`

외부 의존성을 캡슐화한다.

- `search/`: 웹 검색, 특허 검색, 학회/채용 신호 수집 provider
- `llm/`: LLM 기반 보조 판정 provider

`workflow.md` 5단계의 "필요 시 LLM 보조 판정"은 여기서 수용한다.

### `src/config`

변경 가능성이 큰 운영값을 모은다.

- `settings.py`: 전역 설정
- `thresholds.py`: 품질 기준 임계치
- `source_weights.py`: source type별 가중치
- `agent_queries.py`: Agent별 초기 query bundle 템플릿

### `src/prompts`

LLM이나 검색 Agent용 프롬프트 자산을 분리한다.

현재 즉시 필요한 것은 검색 Agent와 품질 보조 판정용 프롬프트다.

### `src/utils`

범용 유틸리티 함수 모음이다.

### `src/models`

enum, 상수, 내부 공통 타입 값을 정리한다.

## `data` 디렉터리 구조

런타임 산출물을 stage별로 나눈다.

- `data/raw/search_runs/`: Agent raw findings 저장
- `data/normalized/evidence_sets/`: 정규화된 evidence set 저장
- `data/quality/reports/`: 품질 리포트 저장
- `data/analysis/`: 7단계 이후 분석 결과 저장

이 구조는 `raw_content` 보존과 stage별 재실행/검증을 쉽게 만든다.

## `tests` 디렉터리 구조

테스트는 fixture, unit, integration으로 나눈다.

- `fixtures/`: raw result, normalized evidence, quality report 예제 데이터
- `unit/`: schema, normalizer, quality gate 단위 테스트
- `integration/`: 3단계부터 5단계까지 이어지는 파이프라인 테스트

현재 1차 구현에서 최소한 아래 테스트는 필요하다.

- 병렬 검색 runner 테스트
- evidence 정규화 테스트
- quality gate 테스트

## `scripts` 디렉터리 구조

개발 중 수동 실행과 smoke test를 위한 스크립트를 둔다.

- `run_pipeline.py`: 전체 stage 실행
- `run_parallel_search.py`: 3단계만 실행
- `run_quality_gate.py`: 5단계만 실행

## Workflow 단계와 디렉터리 매핑

| Workflow 단계 | 주요 디렉터리 |
| --- | --- |
| 1. User Query 입력 | `src/app`, `src/schemas`, `src/utils` |
| 2. Supervisor 초기화 및 실행 계획 수립 | `src/supervisor`, `src/config`, `src/schemas` |
| 3. 병렬 검색 | `src/agents/search`, `src/orchestration`, `src/providers/search` |
| 4. 검색 결과 정규화 및 적재 | `src/normalization`, `src/storage`, `src/schemas` |
| 5. 전역 품질 검증 | `src/quality`, `src/providers/llm`, `src/storage` |
| 6. 재탐색 및 보완 | `src/supervisor`, `src/orchestration`, `src/config` |
| 7. 기술 성숙도 분석 | `src/agents/analysis`, `src/schemas` |
| 8. 위협 수준 분석 | `src/agents/analysis`, `src/schemas` |
| 9. 병합 및 우선순위 매트릭스 생성 | `src/orchestration`, `src/schemas`, `src/storage` |
| 10. 기술 전략 보고서 생성 | `src/agents/analysis`, `src/prompts/analysis` |
| 11. 최종 검토 및 종료 승인 | `src/supervisor`, `src/storage` |

## 현재 우선 생성 대상

지금 바로 구현을 시작한다면 아래 디렉터리부터 만든다.

```text
src/
  agents/
    base/
    search/
  orchestration/
  normalization/
  quality/
  schemas/
  storage/
  providers/
    search/
  config/
tests/
  fixtures/
  unit/
  integration/
data/
  raw/
  normalized/
  quality/
scripts/
```

이 범위면 `workflow.md`의 3~5단계를 구현하는 데 필요한 최소 구조가 갖춰진다.

## 메모

- 저장소가 아직 비어 있으므로 기본 언어는 Python으로 가정한다.
- 이후 프레임워크가 정해지면 `src/` 하위 모듈만 조정하면 되고, stage 중심 분리는 유지하는 것이 좋다.
- `workflow.md`의 "Node 중심 처리 단계", "Central Quality Gate Node", "Supervisor-controlled Retry Stage"는 각각 `normalization`, `quality`, `supervisor` 디렉터리로 대응시켰다.
