# Codex 작업 지시문: 보고서 생성 단계

`workflow.md`의 10. 기술 전략 보고서 생성 단계를 구현해.

구현 전에 먼저 아래 문서를 읽어.

- `service-spec.md`
- `workflow.md`
- `directory.md`

구현 전제:

- Python + LangGraph + LangChain + SQLite 기준으로 구현
- 파일과 모듈 배치는 `directory.md` 기준으로 정리
- 보고서 생성은 분석 재수행이 아니라 synthesis 단계로 구현

구현 범위:

- `src/agents/analysis/report_generation_agent.py`
- `src/schemas/report_output_schema.py`
- report repository 연결
- reference trace 로직
- warning/limitation 반영 로직
- Markdown 또는 HTML 렌더링
- PDF 변환 adapter 또는 placeholder
- fixture 또는 단위 테스트 작성
- canonical analysis output을 소비하는 renderer/repository 연결

입력:

- merged analysis result
- priority matrix
- normalized evidence
- raw_content
- reference metadata
- unresolved/conflict flags

입력 계약은 `service-spec.md`와 `analysis_output_schema.py`를 기준으로 소비만 하며, 상위 schema를 이 문서에서 다시 정의하지 않는다.

필수 출력:

- `SUMMARY`
- `분석 배경`
- `기술 현황`
- `경쟁사 동향`
- `전략적 시사점`
- `REFERENCE`

필수 구현 원칙:

- 보고서는 `raw_content` 직접 참조를 우선할 것
- `key_points`만으로 본문을 만들지 말 것
- 핵심 주장마다 evidence trace가 가능해야 할 것
- TRL 4~6 추정 한계를 명시할 것
- 위협 수준 평가는 TRL 외에도 `Impact`, `Immediacy`, `Execution Credibility`, `Strategic Overlap` 등 복합 요인을 반영한다는 점을 명시할 것
- TRL 수준과 위협 수준이 유의미하게 다를 경우, 그 차이가 발생한 배경과 추가 설명 요인을 보고서에 함께 분석해 제시할 것
- unresolved/conflict가 많으면 warning 또는 재검토 요청을 반영할 것
- 보고서 생성 단계에서 새로운 분석 사실을 만들지 말 것
- 무거운 본문 데이터는 LangGraph state가 아니라 SQLite와 파일 출력에 저장할 것
- final approval 판정은 하지 말고 report artifact만 생성할 것

## 병렬 작업 소유 범위

이 문서는 아래 범위만 소유한다.

- `src/agents/analysis/report_generation_agent.py`
- `src/schemas/report_output_schema.py`
- `src/storage/repositories/report_repository.py`
- `src/prompts/analysis/report_generation_prompt.md`
- `src/config/report_sections.py`
- `src/config/report_warnings.py`

이 문서는 아래 파일을 수정 대상으로 삼지 않는다.

- `src/schemas/normalized_evidence_schema.py`
- `src/schemas/analysis_output_schema.py`
- `src/orchestration/merge_node.py`
- `src/supervisor/`

권장 구현 위치:

- `src/agents/analysis/`
- `src/schemas/`
- `src/storage/repositories/`
- `src/storage/adapters/`
- `src/prompts/analysis/`
- `src/config/`
- `tests/unit/`
- `tests/integration/`
- `data/analysis/reports/`

우선 생성 또는 보강 대상:

```text
src/
  agents/
    analysis/
      report_generation_agent.py
  schemas/
    report_output_schema.py
  storage/
    repositories/
      analysis_result_repository.py
      report_repository.py
    adapters/
      sqlite_adapter.py
  prompts/
    analysis/
      report_generation_prompt.md
  config/
    report_sections.py
    report_warnings.py
  tests/
    unit/
      test_report_generation_agent.py
      test_reference_trace.py
      test_report_warnings.py
    integration/
      test_report_pipeline.py
```

보고서 구현자는 분석 담당자가 생산한 `MergedAnalysisResult`와 `PriorityMatrixRow`를 그대로 소비해야 하며,
필드 부족 시 `service-spec.md` 기준으로 조정 요청을 남기고 독자적으로 분석 schema를 바꾸지 않는다.

구현 순서:

1. `workflow.md`와 `directory.md`를 읽고 요구사항과 파일 배치 기준 확인
2. `report_output_schema.py`와 report repository interface 먼저 고정
3. `report_generation_agent.py` 구현
4. reference trace 로직 구현
5. warning/limitation 삽입 로직 구현
6. Markdown 또는 HTML 렌더링 구현
7. PDF 변환 adapter 또는 placeholder 구현
8. SQLite repository 연결
9. fixture 기반 테스트 작성
10. end-to-end smoke test 수행

수용 기준:

- 필수 6개 섹션이 모두 생성될 것
- 핵심 주장마다 evidence trace가 연결될 것
- TRL 4~6 limitation 문구가 반영될 것
- TRL과 위협 수준 간 괴리가 큰 항목은 그 배경 설명과 추가 요인 분석이 보고서에 포함될 것
- unresolved/conflict warning이 필요한 경우 보고서에 포함될 것
- priority matrix가 보고서에 포함되거나 참조될 것
- Markdown 또는 HTML 산출물과 저장 결과가 생성될 것
- PDF 또는 PDF 변환 가능한 출력 경로가 준비될 것

테스트 기준:

- 필수 섹션 누락 여부
- reference trace 누락 여부
- limitation/warning 반영 여부
- TRL과 위협 수준 불일치 항목의 설명 누락 여부
- 중복 reference 정리 여부
- 동일 입력에서 섹션 순서와 구조가 deterministic 한지
- Markdown/HTML 출력 저장 여부

작업 후 반드시 보고할 것:

- 어떤 부분이 rule-based이고 어떤 부분이 LLM 문장 정리에 의존하는지
- PDF 변환이 실제 구현인지 placeholder인지
- 아직 비어 있는 외부 의존성 또는 가정이 무엇인지
