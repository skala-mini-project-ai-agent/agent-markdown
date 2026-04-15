# 병렬 검색/정규화/품질 검증 구현 작업 계획서

## 1. 문서 목적

이 문서는 `workflow.md`의 아래 3개 단계를 실제 코드로 구현하기 위해 Codex에게 전달할 실행형 작업 계획서다.

- 3. 병렬 검색 단계
- 4. 검색 결과 정규화 및 적재 단계
- 5. 전역 품질 검증 단계

구현 대상은 아래 6개의 병렬 검색 Agent와, 이들의 결과를 후속 분석 단계에서 재사용할 수 있도록 만드는 공통 정규화/적재/품질 검증 파이프라인이다.

구현에 착수하기 전에 Codex는 반드시 `directory.md`를 먼저 확인하고, 디렉터리 구조와 모듈 책임 정의를 기준으로 코드를 배치해야 한다.
공통 서비스 계약과 병렬 작업 ownership은 `service-spec.md`를 우선 기준으로 따른다.

## 2. 구현 범위

이번 작업의 범위는 다음으로 한정한다.

- 6개 Search Agent의 인터페이스와 실행 로직 구현
- Agent 결과를 수용하는 공통 raw result schema 정의
- 정규화 schema 및 적재 구조 정의
- 전역 품질 검증 로직과 pass/fail 판정 구현
- 실패 시 targeted retry를 위한 품질 리포트 구조 정의
- 분석/보고서 단계가 그대로 소비할 수 있는 canonical normalized evidence 계약 준수

이번 작업의 범위에서 제외한다.

- 6단계 재탐색 및 보완 단계의 실제 재실행 오케스트레이션
- 7단계 이후의 TRL 분석, 위협 수준 분석, 보고서 생성
- 외부 UI 구현
- `analysis_output_schema.py`, `report_output_schema.py`의 상세 정의

## 2-1. 구현 기술 스택

이번 구현은 아래 기술 스택을 기본 전제로 한다.

- 언어: Python
- 오케스트레이션: LangGraph
- LLM/도구 래핑: LangChain
- 데이터베이스: SQLite

구현 원칙은 아래와 같다.

- 전체 파이프라인 제어는 `LangGraph` 중심으로 설계한다.
- `LangChain`은 검색 provider 래핑, structured output, LLM 보조 판정 등 보조 계층으로 제한한다.
- Search Agent는 과도한 자율형 AgentExecutor보다, `LangGraph` 노드에서 호출 가능한 예측 가능한 실행 단위로 구현한다.

데이터 저장은 아래 원칙을 따른다.

- 1차 구현은 `SQLite`를 사용한다.
- 테스트와 빠른 실행 검증에서는 `SQLite :memory:` 모드를 사용한다.
- 로컬 디버깅과 재현 가능한 실행을 위해 file-based `SQLite`도 함께 지원한다.
- 저장 계층은 repository/adaptor 형태로 분리해, 필요 시 이후 `DuckDB` 같은 대안 저장소로 확장 가능하게 만든다.

## 3. 구현 목표

구현 결과는 아래 조건을 만족해야 한다.

- 6개 Agent가 병렬 실행된다.
- 각 Agent는 자기 도메인에 맞는 최신 자료를 수집한다.
- 각 Agent 출력은 공통 schema로 정규화 가능해야 한다.
- raw_content와 key_points가 분리 보존된다.
- `signal_type`, `quality_passed`, `unresolved`가 후속 단계에서 재사용 가능하게 유지된다.
- quality gate가 coverage, source diversity, bias, duplicate, low evidence를 점검한다.
- 품질 미달 시 전체 실패가 아니라 부족 영역이 구조적으로 식별된다.

## 3-1. 병렬 작업 소유 범위

이 문서는 아래 범위만 소유한다.

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

이 문서는 아래 파일을 수정 대상으로 삼지 않는다.

- `src/schemas/analysis_output_schema.py`
- `src/schemas/report_output_schema.py`
- `src/agents/analysis/`
- `src/orchestration/merge_node.py`

## 4. 대상 Agent 정의

| Agent | 역할 | 수집 초점 |
| --- | --- | --- |
| PIM Search Agent | PIM 기술 글로벌 동향 수집 | 아키텍처, 제품화, 고객 협업, 양산/검증 신호 |
| CXL Search Agent | CXL 기술 글로벌 동향 수집 | CXL 메모리 확장, 생태계, 표준 대응, 실제 적용 사례 |
| HBM4 Search Agent | HBM4 기술 글로벌 동향 수집 | 로드맵, 성능, 양산 시점, 고객 채택, 경쟁사 발표 |
| Advanced Packaging & Interconnect Agent | 패키징·인터커넥트 동향 수집 | 2.5D/3D 패키징, hybrid bonding, interposer, substrate, interconnect |
| Thermal & Power Management Agent | 열·전력 관리 동향 수집 | 발열 대응, 전력 효율, 냉각 구조, 전력 전달, 시스템 레벨 최적화 |
| Indirect Signal & Patent Agent | 특허·채용·학회 간접 지표 수집 | 특허 출원, 채용 공고, 학회 발표, 컨퍼런스, 조직 투자 신호 |

## 5. 권장 구현 산출물

Codex는 아래 산출물을 우선순위에 따라 구현한다.

1. 병렬 검색 실행 레이어
2. Agent 공통 인터페이스
3. Agent별 query bundle 생성 규칙
4. raw search result schema
5. normalized evidence schema
6. normalization loader
7. quality gate validator
8. quality report 및 retry hint 구조
9. 최소 단위 테스트 또는 샘플 fixture 기반 검증 코드

## 6. 권장 디렉터리 구조

프로젝트 구조의 canonical 기준은 `directory.md`를 따른다.
아래 목록은 이 문서 담당 범위만 발췌한 것이다.

```text
src/
  agents/
    base/
      base_search_agent.py
    search/
      pim_search_agent.py
      cxl_search_agent.py
      hbm4_search_agent.py
      packaging_interconnect_agent.py
      thermal_power_agent.py
      indirect_signal_patent_agent.py
  orchestration/
    parallel_search_runner.py
  schemas/
    raw_result_schema.py
    normalized_evidence_schema.py
    quality_report_schema.py
  normalization/
    evidence_normalizer.py
    evidence_loader.py
    tagging.py
    keypoint_extractor.py
  quality/
    quality_gate.py
    coverage_matrix.py
    deduplication.py
    source_diversity.py
    bias_detection.py
    conflict_detection.py
    confidence_evaluator.py
  tests/
    unit/
      test_parallel_search_runner.py
      test_evidence_normalizer.py
      test_quality_gate.py
```

언어와 프레임워크는 현재 저장소에 코드가 없으므로, 별도 지시가 없으면 Python + LangGraph 기준으로 구현한다.

## 7. 단계별 작업 계획

### Step 1. 공통 계약 정의

먼저 아래 인터페이스를 고정한다.

- Search Agent 입력 계약
- Search Agent 출력 계약
- raw finding 구조
- normalized evidence 구조
- quality report 구조
- analysis/report가 읽을 canonical field 계약

필수 원칙은 아래와 같다.

- Agent별 구현보다 schema를 먼저 고정한다.
- 이후 단계는 모두 이 schema를 기준으로 연결한다.
- raw_content는 절대 유실하지 않는다.
- `service-spec.md`에 정의된 필드를 임의 축소하지 않는다.

### Step 2. 병렬 검색 실행기 구현

`workflow.md` 3단계 구현에 해당한다.

구현 항목:

- 6개 Agent를 병렬 실행하는 runner 구현
- 각 Agent별 query bundle 주입
- 실행 메타데이터 기록
- Agent 단위 실패 격리
- Agent별 로컬 검증 결과 수집

runner의 책임:

- Supervisor가 넘긴 공통 실행 컨텍스트를 각 Agent에 전달
- 병렬 실행 후 결과를 리스트가 아닌 Agent keyed structure로 수집
- 실패 Agent와 성공 Agent를 분리 기록
- 후속 정규화 단계가 읽을 수 있는 raw bundle 생성

권장 결과 구조:

```json
{
  "run_id": "string",
  "executed_at": "ISO-8601",
  "agents": {
    "pim": {
      "status": "success",
      "raw_findings": [],
      "local_validation": {}
    }
  }
}
```

### Step 3. 6개 Search Agent 구현

각 Agent는 공통 베이스 클래스를 상속하거나 동일 인터페이스를 따라야 한다.

필수 메서드:

- `build_queries(context)`
- `search(queries, context)`
- `local_validate(raw_findings)`
- `to_raw_bundle()`

각 Agent 공통 요구사항:

- 최신성 우선 자료 수집
- 최소 출처 수 검사
- 중복 URL 또는 동일 사건 재인용 제거
- 반증 또는 제약 신호 포함 여부 점검
- 결과를 정규화 가능한 단위로 반환

Agent별 추가 수집 포인트:

- `PIM Search Agent`: PIM 제품, 메모리 내 연산, 고객 협력, PoC, 양산 가능성
- `CXL Search Agent`: CXL 2.0/3.0 대응, 메모리 확장 솔루션, 서버/플랫폼 채택
- `HBM4 Search Agent`: HBM4 일정, 성능, 고객사, TSV/적층/전력 이슈
- `Advanced Packaging & Interconnect Agent`: CoWoS, FO-PLP, hybrid bonding, UCIe 관련 신호
- `Thermal & Power Management Agent`: 냉각, 전력 전달망, TSV 열 문제, 시스템 전력 최적화
- `Indirect Signal & Patent Agent`: 특허, 채용, 컨퍼런스, 논문, 조직 투자 간접 증거

### Step 4. 검색 결과 정규화 및 적재 구현

`workflow.md` 4단계 구현에 해당한다.

구현 항목:

- Agent별 raw findings를 공통 schema로 매핑
- `raw_content`와 `key_points` 분리
- `source`, `date`, `company`, `technology`, `source_type` 태깅
- 정규화된 evidence set 저장

정규화 원칙:

- 원문 요약보다 구조 일관성을 우선한다.
- source metadata 누락 시 null 허용 대신 `missing_field_flags`로 기록한다.
- 한 source에서 여러 포인트가 나오면 `raw_content`는 1회 보존하고 `key_points`를 다건 생성 가능하게 설계한다.

권장 normalized evidence schema:

```json
{
  "evidence_id": "string",
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

적재 방식은 우선 아래 둘 중 하나를 선택한다.

- `SQLite :memory:` 기반 적재 구조
- file-based SQLite 저장소 어댑터 분리 구조

Codex는 저장소 결합도를 낮추기 위해 loader interface와 repository interface를 분리해서 구현한다.

### Step 5. 전역 품질 검증 구현

`workflow.md` 5단계 구현에 해당한다.

구현 항목:

- coverage matrix 생성
- source diversity 검사
- duplicate 및 재인용 제거
- company self-promotion 편향 탐지
- conflict, low evidence, low confidence 식별
- 최종 pass/fail 판정

검증은 1차 rule-based로 구현한다.

필수 rule 예시:

- 기술 축별 최소 evidence 수
- 주요 플레이어별 최소 근거 수
- 특정 source type 편중 상한
- 동일 URL, 동일 제목, 동일 이벤트 기반 중복 제거
- 발표성 자료만 존재할 경우 bias flag 부여
- 상충되는 주장 동시 존재 시 conflict flag 부여
- confidence low 비율이 임계치 초과 시 fail 또는 warning 부여

coverage matrix 예시 차원:

- `technology x company`
- 필요 시 `technology x source_type`

품질 검증 결과는 아래처럼 구조화한다.

```json
{
  "status": "pass|fail|warning",
  "coverage": {},
  "source_diversity": {},
  "duplicates_removed": [],
  "bias_flags": [],
  "conflict_flags": [],
  "low_evidence_cells": [],
  "low_confidence_cells": [],
  "retry_recommendations": []
}
```

### Step 6. targeted retry를 위한 출력 준비

이번 범위에서 실제 재실행까지는 하지 않더라도, 6단계와 자연스럽게 연결되도록 아래 데이터는 반드시 남긴다.

- 어떤 Agent가 부족했는지
- 어떤 technology/company cell이 부족했는지
- 어떤 source type이 부족했는지
- 어떤 검색 주제를 보강해야 하는지

즉, quality gate의 출력은 사람이 읽는 리포트가 아니라 Supervisor가 바로 소비 가능한 구조여야 한다.
또한 analysis 담당자가 별도 schema 수정 없이 사용할 수 있어야 한다.

## 8. 구현 순서

Codex는 아래 순서대로 작업한다.

1. `directory.md`를 먼저 읽고 디렉터리 구조와 모듈 책임을 확인
2. `workflow.md` 3~5단계 요구사항을 코드 수준 체크리스트로 변환
3. schema와 interface 먼저 구현
4. 병렬 실행기와 베이스 Agent 구현
5. 6개 Search Agent를 최소 기능으로 구현
6. normalization 및 loader 구현
7. quality gate rule 구현
8. fixture 기반 테스트 작성
9. 샘플 실행으로 end-to-end smoke test 수행

## 9. 수용 기준

아래 조건을 만족하면 1차 구현 완료로 본다.

- 6개 Agent가 동일 인터페이스로 호출된다.
- runner가 병렬 실행 후 결과를 합친다.
- 정규화 결과가 단일 schema로 적재된다.
- raw_content와 key_points가 분리 저장된다.
- quality gate가 pass/fail/warning을 반환한다.
- low evidence, duplicate, bias, conflict가 구조적으로 식별된다.
- 테스트 또는 샘플 실행으로 3단계부터 5단계까지 연결이 검증된다.

## 10. 테스트 계획

최소한 아래 테스트를 포함한다.

### 기능 테스트

- 6개 Agent 결과가 정상 병합되는지
- Agent 일부 실패 시 전체 runner가 중단되지 않는지
- raw result가 normalized evidence로 변환되는지
- duplicate가 제거되는지
- bias/conflict/low evidence가 감지되는지

### 경계 테스트

- 특정 Agent 결과가 0건일 때
- 날짜 없는 source가 들어올 때
- company 태깅이 비어 있을 때
- press release만 과도하게 들어올 때
- 동일 사건을 여러 기사에서 재인용할 때

### 회귀 테스트

- schema 변경 시 기존 fixture가 깨지는지
- quality threshold 조정 시 판정 일관성이 유지되는지

## 11. Codex 작업 지시문 초안

아래 문구를 그대로 또는 약간 수정해서 Codex에게 전달하면 된다.

```md
`workflow.md`의 3. 병렬 검색 단계, 4. 검색 결과 정규화 및 적재 단계, 5. 전역 품질 검증 단계를 구현해.

구현 범위:
- 6개 Search Agent 구현
- 병렬 검색 runner 구현
- raw result schema / normalized evidence schema / quality report schema 구현
- normalization loader 구현
- coverage, source diversity, deduplication, bias/conflict/low evidence 검증이 포함된 quality gate 구현
- fixture 또는 단위 테스트 작성

대상 Agent:
- PIM Search Agent
- CXL Search Agent
- HBM4 Search Agent
- Advanced Packaging & Interconnect Agent
- Thermal & Power Management Agent
- Indirect Signal & Patent Agent

구현 원칙:
- `directory.md`를 먼저 참고해 파일과 모듈을 배치할 것
- `workflow.md`의 용어와 기준을 그대로 반영할 것
- raw_content와 key_points를 분리 저장할 것
- 결과는 targeted retry가 가능하도록 구조화할 것
- 전체 재실행이 아니라 부족 영역 식별이 가능해야 할 것
- 저장소에 코드가 거의 없으므로 Python 기준으로 기본 골격부터 작성할 것

먼저 구현에 필요한 디렉터리 구조와 schema/interface를 만들고, 그 다음 runner, agents, normalization, quality gate, tests 순서로 진행해.
작업 후에는 어떤 가정을 두었는지와 아직 비어 있는 외부 의존성 부분을 명확히 보고해.
```

## 12. 구현 시 주의사항

- 검색 Agent의 실제 외부 검색 API는 추후 바뀔 수 있으므로 provider 종속 코드를 추상화한다.
- 품질 검증 rule은 하드코딩하되 threshold는 설정값으로 분리한다.
- 정규화 단계에서 의미를 과도하게 재해석하지 않는다.
- 간접 지표 Agent 결과는 직접 근거와 섞이지 않도록 source_type과 signal_type을 명확히 구분한다.
- 품질 검증 결과는 사람이 읽기 쉬운 형태보다 기계가 재사용하기 쉬운 구조를 우선한다.
- LangGraph state에는 실행 제어에 필요한 최소 상태만 두고, 대량 evidence는 SQLite에 저장하는 구조를 우선한다.

## 13. 완료 정의

이번 작업이 완료되면 아래가 가능해야 한다.

- Supervisor가 6개 Agent를 병렬 호출할 수 있다.
- 검색 결과가 분석 전 단계에서 바로 사용할 수 있는 normalized evidence set으로 변환된다.
- 품질 부족 영역이 자동 식별되어 6단계 targeted retry로 연결할 수 있다.
