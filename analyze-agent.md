# 분석 단계 구현 작업 계획서

## 목적

이 문서는 `workflow.md`의 아래 단계를 Codex가 실제 코드로 구현할 수 있도록 정리한 실행 계획서다.

- 7. 기술 성숙도 분석 단계
- 8. 위협 수준 분석 단계
- 9. 병합 및 우선순위 매트릭스 생성 단계

구현 전에 반드시 아래 문서를 먼저 읽는다.

- `workflow.md`
- `directory.md`

문서 역할은 다음과 같이 구분한다.

- `service-spec.md`: 서비스 실행 모델, 공통 schema, 병렬 작업 ownership 기준
- `workflow.md`: 단계 목표, 판단 기준, 제어 전략의 원문 기준
- `directory.md`: 디렉터리 구조와 모듈 책임 기준
- `analyze-agent.md`: Codex 구현 순서, 산출물, 규칙, 테스트 기준

## 구현 전제

- 언어는 `Python` 기준으로 구현한다.
- 오케스트레이션은 `LangGraph` 중심으로 구성한다.
- `LangChain`은 structured output, prompt 관리, LLM 보조 판정에 한정한다.
- 데이터 저장은 `SQLite`를 사용한다.
- 테스트는 `SQLite :memory:` 기준으로 수행한다.
- 로컬 재현과 디버깅은 file-based SQLite를 허용한다.

## 구현 범위

이번 작업의 범위는 아래로 한정한다.

- 검증 통과 evidence를 입력으로 사용하는 TRL 분석 로직 구현
- 4축 rubric 기반 Threat 분석 로직 구현
- Merge Node 기반 merged result 및 priority matrix 생성 로직 구현
- 분석 결과 schema 및 저장 구조 구현
- 단위 테스트 또는 fixture 기반 통합 테스트 작성
- canonical normalized evidence 계약을 소비하는 adapter 구현

이번 작업의 범위에서 제외한다.

- 3~5단계 검색/정규화/품질 검증 구현
- 10단계 보고서 생성
- 11단계 최종 검토 및 종료 승인
- 외부 UI
- `normalized_evidence_schema.py` 구조 변경
- `report_output_schema.py` 구조 변경

## 핵심 원칙

- 5단계 품질 검증을 통과한 evidence만 분석 입력으로 사용한다.
- direct evidence와 indirect evidence를 구분한다.
- TRL과 Threat는 다른 질문에 대한 답이므로 동일 점수처럼 섞지 않는다.
- 높은 TRL이 자동으로 높은 Threat로 이어지지 않도록 한다.
- Threat Analysis Agent 내부에서 TRL과의 논리 정합성을 점검하되, 별도 9단계로 분리하지 않는다.
- merge 단계에서는 새로운 해석을 만들지 않는다.
- unresolved 상태는 숨기지 말고 결과 schema에 유지한다.
- 대량 evidence와 분석 결과는 LangGraph state가 아니라 SQLite에 저장한다.

## 구현 대상

이번 문서에서 Codex가 구현해야 하는 주체는 아래와 같다.

| Type | Name | Role |
| --- | --- | --- |
| Agent | Threat Analysis Agent | SK Hynix 기준 위협 수준 평가 |
| Agent | Technology Maturity Analysis Agent | TRL 매트릭스 생성 |
| Node | Merge Node | TRL + 위협 수준 병합, Priority Matrix 생성 |

## 병렬 작업 소유 범위

이 문서는 아래 범위만 소유한다.

- `src/agents/analysis/trl_analysis_agent.py`
- `src/agents/analysis/threat_analysis_agent.py`
- `src/orchestration/merge_node.py`
- `src/schemas/analysis_output_schema.py`
- `src/storage/repositories/analysis_result_repository.py`
- `src/providers/llm/`
- `src/config/strategic_overlap.py`
- `src/prompts/analysis/trl_analysis_prompt.md`
- `src/prompts/analysis/threat_analysis_prompt.md`

이 문서는 아래 파일을 수정 대상으로 삼지 않는다.

- `src/schemas/normalized_evidence_schema.py`
- `src/schemas/quality_report_schema.py`
- `src/agents/analysis/report_generation_agent.py`
- `src/schemas/report_output_schema.py`

## directory.md 기준 구현 위치

- 디렉터리 구조와 파일 배치는 `directory.md`를 기준으로 한다.
- 본 문서에서는 구조를 중복 정의하지 않고, 우선 구현 대상만 지정한다.

이번 단계에서 우선 구현 또는 보강할 위치:

- `src/agents/analysis/`
- `src/schemas/`
- `src/storage/repositories/`
- `src/storage/adapters/`
- `src/providers/llm/`
- `src/prompts/analysis/`
- `src/config/`
- `tests/unit/`
- `tests/integration/`
- `data/analysis/`

우선 생성 또는 보강 대상 파일:

```text
src/
  agents/
    analysis/
      trl_analysis_agent.py
      threat_analysis_agent.py
  orchestration/
    merge_node.py
  schemas/
    analysis_output_schema.py
  storage/
    repositories/
      analysis_result_repository.py
      normalized_evidence_repository.py
      execution_state_repository.py
    adapters/
      sqlite_adapter.py
  providers/
    llm/
      base_llm_provider.py
      llm_judge_provider.py
  config/
    thresholds.py
    strategic_overlap.py
  prompts/
    analysis/
      trl_analysis_prompt.md
      threat_analysis_prompt.md
  tests/
    unit/
      test_trl_analysis_agent.py
      test_threat_analysis_agent.py
      test_merge_node.py
      test_priority_matrix.py
    integration/
      test_analysis_pipeline.py
```

## 단계별 구현 계획

### 1. 분석 입력 계약 고정

7~9단계 구현 전에 입력 계약과 출력 계약을 먼저 고정한다.

입력에 포함되어야 하는 최소 필드:

- `run_id`
- `technology`
- `company`
- `evidence_ids`
- `source_type`
- `quality_passed`
- `confidence`
- `signal_type`

여기서 `signal_type`은 최소 아래 구분을 지원해야 한다.

- `direct`
- `indirect`
- `counter_evidence`

입력 계약 원칙:

- quality gate 통과 결과만 기본 입력으로 사용한다.
- technology x company 셀 기준으로 분석한다.
- direct/indirect/counter evidence를 혼합하지 않고 구분 보존한다.
- 상태 플래그는 schema에 명시적으로 둔다.
- 입력 evidence 계약은 `service-spec.md`의 canonical normalized evidence를 그대로 따른다.

예시 상태 플래그:

- `unresolved`
- `low_confidence`
- `conflict_candidate`

### 2. TRL 분석 구현

`workflow.md` 7단계 구현이다.

구현 항목:

- evidence를 TRL 신호로 매핑
- direct evidence와 indirect evidence 분리
- TRL score 또는 range 산출
- confidence 산출
- rationale 생성
- technology x company 기준 TRL matrix 생성

판단 기준:

- 직접 근거는 샘플 공급, qualification, deployment, 양산, 제품화 발표 같은 신호를 우선한다.
- 간접 근거는 특허, 채용, 조직 신설, 학회 발표, 투자 신호로 제한한다.
- TRL 4~6은 range 기반 추정과 간접 지표 보완을 허용한다.
- 간접 지표만으로 TRL 7~9를 부여하지 않는다.
- 근거 부족 시 `unresolved` 또는 `low_confidence`를 반환한다.

TRL 출력 필드 예시:

```json
{
  "run_id": "string",
  "technology": "HBM4",
  "company": "Company A",
  "trl_range": "6-7",
  "trl_score_low": 6,
  "trl_score_high": 7,
  "confidence": "medium",
  "rationale": "string",
  "direct_evidence_ids": [],
  "indirect_evidence_ids": [],
  "unresolved": false
}
```

### 3. Threat 분석 구현

`workflow.md` 8단계 구현이다.

입력:

- 검증된 evidence
- TRL 결과

구현 항목:

- 4축 rubric 기반 평가
- threat level 또는 tier 산출
- confidence 산출
- rationale 생성
- threat matrix 생성

Threat 평가 4축:

- `Impact`
- `Immediacy`
- `Execution Credibility`
- `Strategic Overlap`

`Strategic Overlap` 점수화 규칙과 SK hynix 관점 가정은 `src/config/strategic_overlap.py`에 모은다.

판단 기준:

- Threat는 단순 기술 성숙도가 아니라 사업 영향과 시간축, 실행력, 자사 로드맵 overlap을 종합해 평가한다.
- 높은 TRL이 자동으로 높은 Threat가 되지 않도록 rule을 둔다.
- `Strategic Overlap`은 SK hynix 관점 가정을 명시적으로 저장한다.
- publicity와 actual risk를 구분한다.
- 기사량보다 adoption, deployment, qualification, 공급망 실행력 근거를 우선한다.

Threat 출력 필드 예시:

```json
{
  "run_id": "string",
  "technology": "HBM4",
  "company": "Company A",
  "threat_level": "high",
  "threat_tier": "tier_1",
  "impact_score": 5,
  "immediacy_score": 4,
  "execution_credibility_score": 5,
  "strategic_overlap_score": 5,
  "confidence": "medium",
  "rationale": "string",
  "assumptions": [],
  "evidence_ids": [],
  "unresolved": false
}
```

### 4. Threat Analysis Agent 내부 정합성 점검 구현

`workflow.md` 8단계 구현에 포함되는 내부 점검 로직이다.

구현 항목:

- TRL-Threat inconsistency 검사
- conflict candidate 셀 식별
- threat rationale 보정
- unresolved 또는 low confidence 상태 확정

핵심 원칙:

- `낮은 TRL + 높은 Threat`는 자동 충돌이 아니다.
- 핵심은 결과 수치가 아니라 근거, 시간축, overlap, 실행력 논리가 서로 모순되는지다.
- Threat Analysis Agent는 위협 평가 중 TRL 결과와의 논리 충돌 가능성을 스스로 점검한다.
- Merge Node는 이미 확정된 TRL 결과와 Threat 결과를 병합만 담당한다.

반드시 검사할 포인트:

- 시간축 불일치
- 자사 관점 미반영
- 직접 근거와 간접 근거의 증거력 혼동
- publicity와 actual risk 혼동
- 근거 부족 대비 과도한 단정

대표 conflict rule 예시:

- TRL 2~3인데 Threat가 `tier_1 immediate`이면 conflict candidate
- TRL 8 이상인데 핵심 사업과 강하게 겹치는 기술에서 Threat가 low면 conflict candidate
- Threat high 근거가 홍보성 기사 위주면 conflict candidate
- TRL high 근거가 간접 지표뿐이면 conflict candidate

Threat 정합성 점검 결과 필드 예시:

```json
{
  "run_id": "string",
  "technology": "PIM",
  "company": "Company A",
  "has_conflict": true,
  "conflict_type": "timeline_mismatch",
  "trl_reference_id": "string",
  "threat_reference_id": "string",
  "resolution_notes": [],
  "confidence_adjustment": "low",
  "unresolved": true
}
```

### 5. Merge Node 구현

`workflow.md` 9단계 구현이다.

이 단계는 `Merge Node`가 담당한다.

구현 항목:

- TRL matrix와 Threat matrix join
- key alignment
- confidence/conflict/unresolved 상태 병합
- deterministic merge
- priority matrix 생성
- 11단계 입력용 통합 구조 생성

병합 기준:

- technology x company key를 기준으로 deterministic merge 수행
- merge 단계에서 새로운 해석을 만들지 않는다
- key mismatch는 조용히 무시하지 말고 오류 또는 retry 가능한 상태로 남긴다
- unresolved conflict는 제거하지 않고 그대로 보존한다

Priority Matrix 최소 필드:

- `technology`
- `company`
- `trl_range`
- `threat_level`
- `merged_confidence`
- `conflict_flag`
- `priority_bucket`
- `action_hint`

초기 `priority_bucket`은 rule-based로 구현한다.

예시:

- high TRL + high Threat + high overlap -> `immediate_priority`
- medium TRL + high Threat + medium/high overlap -> `strategic_watch`
- low TRL + high Threat + strong execution -> `emerging_risk`
- low TRL + low Threat -> `monitor`

## 권장 schema

최소 아래 schema를 먼저 고정한다.

- `TRLAnalysisResult`
- `ThreatAnalysisResult`
- `ConflictResolutionResult`
- `MergedAnalysisResult`
- `PriorityMatrixRow`

우선 구현 위치:

- `src/schemas/analysis_output_schema.py`

## SQLite 저장 전략

분석 결과는 SQLite에 저장한다.

기본 원칙:

- 테스트는 `SQLite :memory:` 사용
- 로컬 재현은 file-based SQLite 허용
- LangGraph state에는 참조값과 상태만 저장
- 상세 결과와 rationale은 DB 저장
- report 단계가 이 결과를 그대로 소비할 수 있도록 deterministic key를 유지

권장 저장 테이블:

- `trl_analysis_results`
- `threat_analysis_results`
- `conflict_resolution_results`
- `merged_analysis_results`
- `priority_matrix_rows`

공통 저장 키:

- `run_id`
- `technology`
- `company`
- `stage_name`
- `version`

## LangGraph 구현 방향

권장 stage 흐름:

```text
quality_passed_evidence
  -> technology_maturity_analysis_agent
  -> threat_analysis_agent
  -> merge_node
```

분석 단계의 입력은 search 담당자가 생산한 canonical normalized evidence와 quality report를 그대로 사용한다.
필드 부족을 이유로 search 문서 범위의 schema를 재정의하지 않는다.

권장 상태 필드:

- `run_id`
- `analysis_scope`
- `trl_result_refs`
- `threat_result_refs`
- `merged_result_refs`
- `needs_review`

상태 설계 원칙:

- TRL과 Threat는 분리 계산한다.
- Threat는 TRL 결과를 참고 입력으로 사용할 수 있다.
- merge는 항상 deterministic 하게 동작해야 한다.

## 구현 순서

Codex는 아래 순서대로 작업한다.

1. `directory.md`를 먼저 읽고 파일 배치 기준을 확인
2. `workflow.md`의 7~9단계 요구사항을 코드 체크리스트로 변환
3. `analysis_output_schema.py`와 repository interface를 먼저 고정
4. `trl_analysis_agent.py` 구현
5. `threat_analysis_agent.py` 구현
6. Threat Analysis Agent 내부 정합성 점검 로직 구현
7. `merge_node.py` 및 priority matrix 생성 로직 구현
8. SQLite repository 연결
9. fixture 기반 테스트 작성
10. end-to-end smoke test 수행

## 수용 기준

아래 조건을 만족하면 1차 구현 완료로 본다.

- 각 technology x company 셀에 대해 TRL 결과가 생성된다.
- 각 technology x company 셀에 대해 Threat 결과가 생성된다.
- rationale과 confidence가 각 결과에 포함된다.
- Threat 결과 내부에 conflict candidate 또는 low confidence 조정 결과가 남는다.
- Merge Node를 통해 merged result와 priority matrix가 동일 schema 체계로 생성된다.
- SQLite 저장과 조회가 가능하다.
- 테스트 또는 샘플 실행으로 7~9단계 연결이 검증된다.

## 테스트 계획

최소 아래 테스트를 포함한다.

- direct evidence와 indirect evidence가 TRL에서 다르게 처리되는지
- Threat 분석이 4축 rubric을 모두 채우는지
- 낮은 TRL + 높은 Threat를 자동 충돌로 처리하지 않는지
- 명백한 시간축 불일치를 Threat 내부 정합성 점검에서 잡는지
- Merge Node가 deterministic 하게 동작하는지
- priority bucket이 규칙대로 계산되는지
- evidence 부족 셀을 unresolved로 처리하는지
- key mismatch가 발생했을 때 오류 상태가 남는지

## Codex 작업 지시문 초안

```md
`workflow.md`의 7. 기술 성숙도 분석 단계, 8. 위협 수준 분석 단계, 9. 병합 및 우선순위 매트릭스 생성 단계를 구현해.

구현 전제:
- 먼저 `directory.md`를 읽고 디렉터리 구조와 모듈 책임을 기준으로 파일을 배치할 것
- `workflow.md`의 용어와 판단 기준을 그대로 반영할 것
- Python + LangGraph + LangChain + SQLite 기준으로 구현할 것

구현 범위:
- `trl_analysis_agent.py`
- `threat_analysis_agent.py`
- `merge_node.py` 및 priority matrix 생성 로직
- `analysis_output_schema.py`
- SQLite repository 연결
- fixture 또는 단위 테스트 작성

구현 원칙:
- 품질 검증 통과 evidence만 분석 입력으로 사용할 것
- TRL과 Threat를 혼동하지 말 것
- Threat는 Impact, Immediacy, Execution Credibility, Strategic Overlap 4축으로 평가할 것
- 낮은 TRL + 높은 Threat를 자동 충돌로 처리하지 말 것
- Threat Analysis Agent 내부에서 TRL과의 정합성을 점검할 것
- conflict candidate 또는 low confidence 조정 결과를 Threat 결과에 남길 것
- Merge Node는 새로운 해석을 만들지 말 것
- 대량 결과는 LangGraph state가 아니라 SQLite에 저장할 것

작업 순서:
- schema와 repository를 먼저 고정
- TRL -> Threat -> Merge Node 순으로 구현
- 마지막에 테스트와 smoke test를 수행

작업 후에는 아래를 명확히 보고할 것:
- 어떤 scoring/threshold 가정을 두었는지
- 어떤 부분이 rule-based이고 어떤 부분이 LLM 보조 판정인지
- 아직 비어 있는 외부 의존성 또는 가정이 무엇인지
```

## 구현 시 주의사항

- TRL 고평가의 가장 흔한 원인은 간접 지표를 직접 근거처럼 쓰는 것이다.
- Threat 과대평가의 가장 흔한 원인은 publicity를 execution risk로 오인하는 것이다.
- `Strategic Overlap`은 반드시 SK hynix 관점 가정을 함께 저장해야 한다.
- 충돌 조정은 “누가 맞나”보다 “어느 논리가 약한가”를 드러내는 형태가 좋다.
- Merge Node는 계산 노드가 아니라 정렬 및 병합 노드로 유지한다.

## 완료 정의

- quality gate 통과 evidence로부터 TRL 분석 결과를 생성할 수 있다.
- 같은 입력으로 Threat 분석 결과를 생성할 수 있다.
- Threat Analysis Agent 내부에서 두 결과 간 논리 정합성을 점검할 수 있다.
- Merge Node를 통해 최종적으로 전략 우선순위 판단에 사용할 Priority Matrix를 생성할 수 있다.
