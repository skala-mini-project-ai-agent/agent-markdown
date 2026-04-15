# Codex 작업 지시문: Supervisor 구현

`service-spec.md`, `workflow.md`, `parallel-search-implementation-plan.md`, `analyze-agent.md`, `report-agent.md`, `directory.md`를 기준으로 전체 파이프라인을 통제하는 `Supervisor`를 구현해.

구현 전에 먼저 아래 문서를 읽어.

- `workflow.md`
- `service-spec.md`
- `directory.md`
- `parallel-search-implementation-plan.md`
- `analyze-agent.md`
- `report-agent.md`

## 구현 전제

- Python + LangGraph + LangChain + SQLite 기준으로 구현
- 파일과 모듈 배치는 `directory.md` 기준으로 정리
- Supervisor는 분석 Agent가 아니라 orchestration/controller 계층으로 구현
- 각 stage의 실질 계산은 search/analysis/report agent나 node가 수행하고, Supervisor는 실행 순서, gate, retry, 승인만 담당
- final approval의 단일 기록 주체는 Supervisor로 고정

## 구현 목표

Supervisor는 아래를 일관되게 수행해야 한다.

- 사용자 입력을 실행 가능한 분석 과제로 정리
- 탐색 모드와 기술 축을 확정
- Search Agent별 query bundle 생성
- stage 진입/종료 조건 관리
- 품질 검증 실패 시 targeted retry 대상 지정
- analysis/report stage로의 진입 여부 결정
- 최종 보고서의 종료 승인 또는 보완 요청 결정

## Supervisor 책임 범위

구현 범위:

- `workflow.md` 2단계 Supervisor 초기화 및 실행 계획 수립
- `workflow.md` 6단계 재탐색 및 보완 제어
- `workflow.md` 11단계 최종 검토 및 종료 승인 제어
- 각 stage 사이의 gate 관리
- 실행 상태 저장과 retry count 관리

구현 범위에서 제외:

- 병렬 검색 Agent 내부 로직
- 정규화 로직
- 품질 검증 rule 자체
- TRL/Threat 계산 로직
- 보고서 본문 생성 로직

## 핵심 원칙

- 각 단계는 Supervisor 승인 없이는 다음 단계로 진입하지 않는다.
- 전체 재실행은 금지하고 targeted retry만 허용한다.
- retry는 최대 2회까지 허용한다.
- raw_content와 key_points 분리 정책은 초기화 시점에 강제한다.
- quality gate fail 시 부족 영역만 재실행 대상으로 지정한다.
- analysis stage는 quality-passed evidence만 사용하도록 강제한다.
- report stage는 merged analysis result와 trace 가능한 evidence가 있을 때만 진입시킨다.
- 최종 승인 단계에서는 보고서 품질 기준을 체크하고, 미충족 시 필요한 단계만 부분 재진입시킨다.

## 구현 대상

이번 문서에서 Codex가 구현해야 하는 주체는 아래와 같다.

| Type | Name | Role |
| --- | --- | --- |
| Supervisor | Central Supervisor | 전체 pipeline 계획 수립, gate 통제, retry 제어, 종료 승인 |
| Module | Stage Gate | 단계 진입/통과/실패 판정 관리 |
| Module | Retry Controller | targeted retry 대상 계산 및 제한 관리 |
| Module | Planning | 초기 query bundle, scope, mode 생성 |

## directory.md 기준 구현 위치

- `src/supervisor/`
- `src/orchestration/`
- `src/schemas/`
- `src/storage/repositories/`
- `src/storage/adapters/`
- `src/config/`
- `tests/unit/`
- `tests/integration/`

우선 생성 또는 보강 대상:

```text
src/
  supervisor/
    supervisor.py
    planning.py
    retry_controller.py
    stage_gate.py
  orchestration/
    stage_executor.py
    execution_context.py
  schemas/
    query_schema.py
    quality_report_schema.py
    analysis_output_schema.py
    report_output_schema.py
    supervisor_state_schema.py
  storage/
    repositories/
      execution_state_repository.py
      quality_report_repository.py
      analysis_result_repository.py
      report_repository.py
    adapters/
      sqlite_adapter.py
  config/
    settings.py
    thresholds.py
    agent_queries.py
  tests/
    unit/
      test_supervisor_planning.py
      test_stage_gate.py
      test_retry_controller.py
      test_final_approval.py
    integration/
      test_supervisor_pipeline_flow.py
```

## Supervisor가 통제할 stage 흐름

권장 흐름:

```text
input_normalization
  -> supervisor_planning
  -> parallel_search
  -> normalization_and_load
  -> global_quality_gate
  -> targeted_retry_if_needed
  -> technology_maturity_analysis
  -> threat_analysis
  -> merge_node
  -> report_generation
  -> final_approval
```

조건부 흐름:

- quality gate `pass` -> analysis stage 진행
- quality gate `fail` + retry 가능 -> targeted retry 진행
- quality gate `fail` + retry 한도 초과 -> unresolved 상태로 다음 단계 진행 여부 판단
- final approval `fail` -> 필요한 직전 단계만 부분 재진입

## 단계별 구현 계획

### 1. Supervisor 상태 계약 고정

먼저 Supervisor state를 고정한다.

최소 상태 필드:

- `run_id`
- `user_query`
- `analysis_scope`
- `technology_axes`
- `mode`
- `query_bundles`
- `stage_status`
- `retry_counts`
- `quality_report_ref`
- `analysis_result_refs`
- `report_ref`
- `approval_status`
- `needs_review`

상태 설계 원칙:

- LangGraph state에는 제어에 필요한 상태와 ref만 저장
- 대량 evidence, matrix, report 본문은 SQLite나 파일 저장소에 보관
- stage 상태는 `pending | in_progress | passed | failed | skipped` 정도로 표준화

### 2. 초기 계획 수립 구현

`workflow.md` 2단계 구현이다.

구현 항목:

- 분석 목적 정리
- 기술 축 확정
- 탐색 방식 결정
- Search Agent별 query bundle 생성
- 실행 메타데이터 초기화
- stage gate 등록

판단 기준:

- 경쟁사 사전 지정 여부 식별
- 경쟁사 미지정 시 `open exploration mode`
- 기술 축은 HBM4 / PIM / CXL / Advanced Packaging / Thermal·Power 중심으로 관리
- raw_content / key_points 분리 정책 등록

### 3. Stage Gate 구현

Supervisor는 각 단계 진입 조건과 산출물 유효성을 검사해야 한다.

필수 gate 예시:

- 검색 stage 시작 전: query bundle 존재 여부
- 정규화 stage 시작 전: raw findings 존재 여부
- 분석 stage 시작 전: quality gate pass 또는 unresolved 허용 정책 확인
- merge stage 시작 전: TRL 결과와 Threat 결과 존재 여부
- report stage 시작 전: merged result, priority matrix, reference trace 가능성 확인
- final approval 전: 보고서 필수 섹션 및 reference 충족 여부 확인

Stage Gate는 아래를 반환할 수 있어야 한다.

- `pass`
- `fail`
- `retry`
- `blocked`

### 4. targeted retry 제어 구현

`workflow.md` 6단계 구현이다.

구현 항목:

- quality report에서 부족 셀 식별
- 부족한 agent/technology/source_type 매핑
- query 수정 또는 보강 지시 생성
- retry count 갱신
- 최대 2회 제한 적용

retry 원칙:

- 전체 파이프라인 재실행 금지
- 부족한 Search Agent만 선택 실행
- 동일 셀의 반복 실패는 unresolved로 넘길 수 있어야 함
- retry 사유와 retry 대상은 구조적으로 남겨야 함

retry 출력 예시:

```json
{
  "run_id": "string",
  "retry_targets": [
    {
      "agent": "hbm4",
      "technology": "HBM4",
      "company": "Company A",
      "reason": "low_evidence"
    }
  ],
  "retry_allowed": true,
  "retry_count": 1
}
```

### 5. analysis/report stage 진입 통제 구현

Supervisor는 7~10단계와 보고서 단계로 넘어갈 때 입력 충족 여부를 확인해야 한다.

분석 단계 진입 조건:

- quality report 존재
- quality gate 통과 또는 unresolved 허용 정책 명확화
- normalized evidence set 접근 가능

보고서 단계 진입 조건:

- merged result 존재
- priority matrix 존재
- reference metadata 접근 가능
- unresolved/conflict/warning 정보 포함 가능

### 6. 최종 검토 및 종료 승인 구현

`workflow.md` 11단계 구현이다.

구현 항목:

- 보고서 6개 목차 충족 여부 확인
- reference trace 가능 여부 확인
- priority matrix 포함 여부 확인
- unresolved/conflict 항목 명시 여부 확인
- PDF 또는 대체 산출물 생성 여부 확인
- 승인 또는 보완 요청 판정

최종 승인 원칙:

- Supervisor가 최종 승인권을 가진다.
- 미충족 시 전체 재실행이 아니라 필요한 단계만 부분 재진입
- 종료 상태는 `approved | revision_required | blocked` 정도로 관리

## 권장 schema

최소 아래 schema를 먼저 고정한다.

- `SupervisorState`
- `StageStatus`
- `RetryPlan`
- `ApprovalDecision`

우선 구현 위치:

- `src/schemas/supervisor_state_schema.py`

## SQLite 저장 전략

Supervisor 관련 상태는 SQLite에 저장한다.

권장 저장 테이블:

- `execution_runs`
- `stage_statuses`
- `retry_plans`
- `approval_decisions`

공통 저장 키:

- `run_id`
- `stage_name`
- `version`
- `updated_at`

## 구현 순서

Codex는 아래 순서대로 작업한다.

1. `workflow.md`, `directory.md`, `parallel-search-implementation-plan.md`, `analyze-agent.md`, `report-agent.md`를 읽고 책임 경계를 정리
2. `supervisor_state_schema.py`와 execution state repository부터 고정
3. `planning.py` 구현
4. `stage_gate.py` 구현
5. `retry_controller.py` 구현
6. `supervisor.py` 구현
7. `stage_executor.py`와 LangGraph 흐름 연결
8. SQLite repository 연결
9. unit/integration 테스트 작성
10. end-to-end smoke test 수행

## 수용 기준

- Supervisor가 query bundle과 실행 상태를 초기화할 수 있다.
- stage별 진입/통과/실패를 일관되게 판정할 수 있다.
- quality gate fail 시 targeted retry plan을 생성할 수 있다.
- retry 한도 초과 시 unresolved 또는 blocked 상태를 기록할 수 있다.
- analysis/report/final approval 단계 진입 조건을 강제할 수 있다.
- 최종 산출물에 대해 승인 또는 보완 요청을 결정할 수 있다.
- SQLite에 실행 상태, retry, approval 결과를 저장/조회할 수 있다.

## 테스트 기준

- 경쟁사 미지정 시 `open exploration mode`로 초기화되는지
- Search Agent별 query bundle이 생성되는지
- stage gate가 필수 입력 누락을 막는지
- quality fail 시 targeted retry만 생성되는지
- retry count가 2회를 넘지 않는지
- merged result 없이 report stage 진입이 차단되는지
- 필수 보고서 섹션 누락 시 final approval이 fail 되는지
- 필요한 직전 단계만 부분 재진입 대상으로 남기는지

## 작업 후 반드시 보고할 것

- 어떤 gate가 rule-based인지
- 어떤 승인/재시도 판단이 설정값에 의존하는지
- unresolved를 어느 단계에서 어떻게 허용했는지
- 아직 비어 있는 외부 의존성 또는 가정이 무엇인지
