# **전체 Workflow 단계 정의**

## 서비스 관점 전제

- 이 문서는 내부 stage workflow를 정의한다.
- 서비스 외부 인터페이스와 공통 schema ownership은 `service-spec.md`를 따른다.
- 최종 승인 책임은 Supervisor에 고정한다.
- 3~5단계, 7~9단계, 10단계는 병렬 개발 가능해야 하므로 stage 간 입출력 계약을 명시적으로 유지한다.

## **1. User Query 입력 단계**

### **Goal**

사용자의 요청을 시스템이 실행 가능한 분석 과제로 해석한다.

### **Criteria**

- 분석 목적이 명확히 해석되어야 한다.
- 출력물이 기술 전략 보고서라는 점이 확정되어야 한다.
- 경쟁사 사전 지정 여부, 최신성 기준, 분석 대상 기술 축이 식별되어야 한다.

### **Task**

- 사용자 질의 수신
- 핵심 목표 파악
- 기술 도메인 식별
- 제약 조건 및 출력 형식 식별

### **Control Strategy**

- 입력이 모호하더라도 기본 실행 가능한 형태로 정규화한다.
- 경쟁사 미지정 시 기본값은 open exploration mode로 둔다.

### **Structure**

- **Input Stage**
- Supervisor 진입 전 초기 입력 해석 단계
- 서비스 요청 생성 단계

---

## **2. Supervisor 초기화 및 실행 계획 수립 단계**

### **Goal**

전체 파이프라인이 일관되게 동작하도록 분석 범위, 탐색 방식, 초기 실행 계획을 확정한다.

### **Criteria**

- 분석 대상 기술 축이 확정되어야 한다.
- 탐색 방식이 확정되어야 한다.
    - seed competitor mode / open exploration mode
- Search Agent별 초기 query bundle이 생성되어야 한다.
- 실행 메타데이터와 retry 정책이 초기화되어야 한다.

### **Task**

- 기술 축 확정
- 경쟁사 탐색 모드 결정
- Search Agent별 초기 query bundle 생성
- 실행 상태 초기화
- stage gate 등록

### **Control Strategy**

- 각 단계는 Supervisor 승인 없이는 다음 단계로 진입할 수 없다.
- 전체 재실행 금지, targeted retry, 최대 2회 재시도 규칙을 미리 등록한다.
- raw_content와 key_points 분리 정책을 초기화한다.

### **Structure**

- **Central Supervisor Stage**

---

## **3. 병렬 검색 단계**

### **Goal**

기술 도메인별 최신 자료와 근거를 병렬 수집하고, 잠재 경쟁사와 핵심 기술 신호를 포괄적으로 확보한다.

### **Criteria**

- (User Query에 특정 기업이 없을 경우) 특정 기업 편향 없이 플레이어가 자연 발굴되어야 한다.
- 각 Search Agent가 최소한의 로컬 검증을 완료해야 한다.
    - 각 기술 축별 evidence가 수집되어야 한다.
    - agent의 역할(탐색 주제)에 따른 evidence가 수집되어야 함
- (User Query에 최신성 기준이 없을 경우) 수집된 정보의 80% 이상이 2024~2026년 최신 자료

### **Task**

- 6개 Search Agent 병렬 실행
- 기술별 검색 수행
- 반증/제약 근거 수집
- 간접 지표 수집
- 경쟁사 및 플레이어 식별
- 로컬 검증 수행

### **Control Strategy**

- Search Agent들은 병렬로 실행한다.
- 각 Agent는 자기 결과에 대해 최신성, 최소 출처 수, 중복 제거, 반증 포함 여부를 로컬 체크한다.
- 결과는 공통 schema로 정규화 가능한 형태로 반환한다.

### **Structure**

- **Distributed Search Stage**

---

## **4. 검색 결과 정규화 및 적재 단계**

### **Goal**

병렬로 수집된 raw findings를 공통 schema로 정리하고 후속 검증·분석이 가능한 상태로 적재한다.

### **Criteria**

- 모든 수집 결과가 공통 output schema에 맞게 정규화되어야 한다.
- raw_content와 key_points가 분리 저장되어야 한다.
- source metadata, company, technology 태깅이 완료되어야 한다.
- `signal_type`, `quality_passed`, `unresolved` 등 후속 분석용 상태 필드가 유지되어야 한다.

### **Task**

- raw findings 수집
- 공통 schema 매핑
- source/date/company/technology tagging
- raw_content 저장
- key_points 분리 생성
- normalized evidence set 적재

### **Control Strategy**

- 원문 손실을 방지하기 위해 raw_content는 반드시 별도 보존한다.
- 정규화 과정에서는 의미 압축보다 구조 일관성을 우선한다.
- canonical normalized evidence 계약은 `service-spec.md`를 따른다.

### **Structure**

- **Normalization Stage**
- Node 중심 처리 단계

---

## **5. 전역 품질 검증 단계**

### **Goal**

전체 evidence set이 분석 단계로 넘어갈 수 있을 만큼 충분하고 균형 잡혀 있는지 전역 기준으로 검증한다.

### **Criteria**

- 기술×경쟁사 coverage가 일정 수준 이상 확보되어야 한다.
- 출처 유형 다양성이 충족되어야 한다.
- 기업 발표 편중이 과도하지 않아야 한다.
- 중복/재인용 제거가 되어야 한다.
- low evidence, conflict, low confidence 셀이 식별되어야 한다.

### **Task**

- coverage matrix 생성
- source diversity 검사
- 중복 제거
- bias flagging
- conflict / low evidence / low confidence 식별
- pass/fail 판정

### **Control Strategy**

- 1차는 rule-based 검증
- 필요 시 LLM 보조 판정
- fail 시 전체 재실행이 아니라 부족한 Search Agent만 targeted retry
- retry는 최대 2회 제한

### **Structure**

- **Quality Gate Stage**
- Central Quality Gate Node

---

## **6. 재탐색 및 보완 단계**

### **Goal**

전역 검증에서 부족하다고 판정된 영역만 선택적으로 보완하여 전체 evidence 품질을 끌어올린다.

### **Criteria**

- 부족 셀이 명확히 특정되어야 한다.
- 해당 기술/에이전트만 선택적으로 재실행되어야 한다.
- 재시도 횟수 제한을 넘지 않아야 한다.

### **Task**

- fail 원인 분석
- 대상 Search Agent 지정
- query 수정
- targeted retry 실행
- 보완 결과 재정규화 및 재검증

### **Control Strategy**

- Supervisor가 재탐색 대상을 지정한다.
- 전체 파이프라인을 다시 돌리지 않는다.
- 최대 2회 재시도 후에도 미충족 시 unresolved 상태로 다음 단계에 넘길 수 있다.
- unresolved를 넘길 경우 quality report와 analysis output에 동일하게 남긴다.

### **Structure**

- **Supervisor-controlled Retry Stage**

---

## **7. 기술 성숙도 분석 단계**

### **Goal**

검증된 evidence를 기반으로 경쟁사별 기술 성숙도를 TRL 기준으로 추정한다.

### **Criteria**

- 각 기술×경쟁사 셀에 대해 TRL 단계 또는 범위가 산출되어야 한다.
- 모든 판단에 근거 evidence와 confidence가 병기되어야 한다.
- TRL 4~6은 범위 기반 추정과 간접 지표 보완이 반영되어야 한다.
- 근거 부족 시 unresolved 처리되어야 한다.

### **Task**

- evidence를 TRL 신호로 매핑
- 직접 근거/간접 근거 구분
- TRL range 및 confidence 산출
- rationale 생성
- TRL matrix 생성

### **Control Strategy**

- 검증 통과 evidence만 사용한다.
- 과도한 단정은 금지한다.

### **Structure**

- **Technology Maturity Analysis Stage**
- Analysis Agent 또는 Analysis Node

---

## **8. 위협 수준 분석 단계**

### **Goal**

경쟁사별 기술 동향이 SK hynix의 R&D 우선순위에 미치는 위협 수준을 평가한다.

### **Criteria**

- 각 기술×경쟁사 셀에 대해 threat level이 산출되어야 한다.
- Impact, Immediacy, Execution Credibility, Strategic Overlap 기준이 반영되어야 한다.
    - 
        
        이 기준은 위협 수준을 평가하는 4개 축을 설명한다.
        
        즉, 어떤 경쟁사가 어떤 기술에서 자사에 얼마나 위협적인지를 아래 4가지 질문으로 분해해 판단한다.
        
        ## **1. Impact**
        
        **그 기술이 우리 사업에 미치는 영향이 얼마나 큰가?**
        
        쉽게 말하면 해당 경쟁사가 그 기술에서 앞설 때 SK hynix 사업에 미치는 직접 영향도를 평가하는 축이다.
        
        예를 들면:
        
        - HBM4에서 경쟁사가 앞서면 → 우리 핵심 메모리 사업에 직접 영향 → **Impact 높음**
        - CXL 관련 생태계 툴 하나 잘 만든 회사 → 중요하긴 하지만 직접 타격은 제한적일 수 있음 → **Impact 중간**
        - 아직 실험적 PIM 아이디어만 있는 스타트업 → 현재 직접 영향은 작을 수 있음 → **Impact 낮음**
        
        즉 영향 범위와 강도를 본다.
        
        ---
        
        ## **2. Immediacy**
        
        **그 위협이 얼마나 빨리 현실이 되나?**
        
        쉽게 말하면 이 위협이 12~24개월 안에 현실화되는지 보는 축이다.
        
        예를 들면:
        
        - 이미 샘플 공급, 고객 qualification, 양산 일정이 보이는 경우 → **Immediacy 높음**
        - 논문, 특허, 연구 발표만 있고 상용화 신호가 약한 경우 → **Immediacy 낮음**
        
        즉 위협의 시간축을 본다.
        
        ---
        
        ## **3. Execution Credibility**
        
        **그 회사가 정말 해낼 수 있는 회사인가?**
        
        쉽게 말하면 발표 수준이 아니라 실제 실행 가능성을 판단하는 축이다.
        
        이건 보통 이런 걸로 판단함:
        
        - 실제 양산 경험
        - 고객사 관계
        - 공급망/패키징 역량
        - 자본력
        - 과거 로드맵 이행력
        - 관련 인력/조직/투자 규모
        
        예를 들면:
        
        - 메모리/패키징/양산 경험이 풍부한 대형 업체 → **Execution Credibility 높음**
        - 발표는 많이 하지만 실제 제품화 이력이 거의 없는 업체 → **낮음**
        
        즉 실행력의 신뢰도를 본다.
        
        ---
        
        ## **4. Strategic Overlap**
        
        **그 기술이 우리 핵심 로드맵과 얼마나 직접 겹치나?**
        
        쉽게 말하면 그 기술 방향이 자사 핵심 로드맵과 얼마나 직접 충돌하는지 보는 축이다.
        
        예를 들면:
        
        - 우리도 HBM4, advanced packaging을 핵심 우선순위로 두고 있는데 경쟁사도 거기서 빠르게 앞선다 → **Overlap 높음**
        - 경쟁사는 CXL 스위치 쪽에 강한데 우리는 현재 메모리 본체가 핵심이다 → **Overlap은 중간 또는 낮음**
        - 연구는 비슷해 보여도 우리 사업 우선순위와 직접 연결되지 않으면 → **Overlap 낮음**
        
        즉 남의 일반적 강점이 아니라 자사와 겹치는 강점을 본다.
        
        ---
        
        ## **이 4개를 왜 같이 보냐**
        
        한 축만 보면 판단이 왜곡되기 때문이야.
        
        예를 들어:
        
        ### **사례 1**
        
        어떤 기술이 엄청 성숙함
        
        → 그런데 우리 핵심 사업과 안 겹침
        
        → **TRL은 높아도 위협은 낮을 수 있음**
        
        ### **사례 2**
        
        아직 TRL은 낮음
        
        → 그런데 우리 핵심 로드맵과 정면으로 겹치고, 그 회사 실행력이 강함
        
        → **당장 양산은 아니어도 전략적 위협은 높을 수 있음**
        
        즉 위협 수준은
        
        - *“기술이 얼마나 발전했나”만 보는 게 아니라,
        
        “우리에게 얼마나 크고, 얼마나 빨리, 얼마나 현실적으로, 얼마나 직접적으로 들어오나”**를 보는 거야.
        
        ---
        
        ## **네 프로젝트 문맥으로 풀면**
        
        예를 들어 경쟁사의 HBM4를 평가할 때:
        
        - **Impact**: HBM4가 SK hynix 핵심 사업에 직접 영향 주나?
        - **Immediacy**: 이 경쟁사의 HBM4 진전이 12~24개월 안에 현실 위협이 되나?
        - **Execution Credibility**: 이 회사가 실제로 샘플→qualification→양산까지 갈 수 있나?
        - **Strategic Overlap**: 이 기술 방향이 SK hynix의 핵심 R&D 우선순위와 직접 겹치나?
        
        이 4개를 종합해서
        
        “위협 높음 / 중간 / 낮음”을 판단하는 거임.
        
        ---
        
        ## **한 줄 정의로 문서에 쓰려면**
        
        이렇게 적으면 깔끔해.
        
        **위협 수준은 단순 기술 성숙도만으로 판단하지 않고, 해당 기술이 SK hynix 핵심 사업에 미치는 영향도(Impact), 12~24개월 내 현실화 가능성(Immediacy), 경쟁사의 실제 실행력(Execution Credibility), 자사 핵심 로드맵과의 충돌 정도(Strategic Overlap)를 종합해 평가한다.**
        
- TRL과 위협 수준을 혼동하지 않아야 한다.
- rationale과 confidence가 함께 제공되어야 한다.

### **Task**

- 검증된 evidence와 TRL 결과 입력
- 4축 rubric 기반 위협 수준 평가
- tier 분류
- threat matrix 생성

### **Control Strategy**

- 높은 TRL이 자동으로 높은 위협으로 이어지지 않도록 rule을 둔다.
- 자사 전략과의 overlap 가정은 명시적으로 표시한다.
- Threat 판단 과정에서 TRL 결과와의 논리 정합성을 내부 점검한다.
- 명백한 시간축 불일치, publicity 과대해석, 근거 수준 불일치는 threat 결과의 confidence 조정 또는 unresolved flag로 반영한다.

### **Structure**

- **Threat Profiling Stage**
- Analysis Agent

---

## **9. 병합 및 우선순위 매트릭스 생성 단계**

### **Goal**

TRL 결과와 Threat 결과를 하나의 통합 분석 결과로 병합하고, 전략 우선순위 판단이 가능한 Priority Matrix를 생성한다.

### **Criteria**

- 모든 기술×경쟁사 셀이 동일 schema로 병합되어야 한다.
- TRL, Threat, Confidence, Conflict Flag가 함께 정리되어야 한다.
- Priority Matrix가 생성되어야 한다.

### **Task**

- TRL matrix와 Threat matrix join
- key alignment
- confidence/conflict flag 병합
- priority matrix 생성
- 보고서 입력용 통합 구조 생성

### **Control Strategy**

- deterministic merge 수행
- 병합 과정에서 새로운 해석은 만들지 않는다
- key mismatch가 있으면 이전 단계로 반환한다

### **Structure**

- **Merge Stage**
- Merge Node

---

## **10. 기술 전략 보고서 생성 단계**

### **Goal**

통합 분석 결과와 raw_content를 바탕으로 R&D 담당자가 바로 사용할 수 있는 전략 분석 보고서를 생성한다.

### **Criteria**

- SUMMARY / 분석 배경 / 기술 현황 / 경쟁사 동향 / 전략적 시사점 / REFERENCE가 모두 포함되어야 한다.
- 핵심 주장마다 출처 trace가 가능해야 한다.
- TRL 4~6 추정 한계가 명시되어야 한다.
- 전략적 시사점이 행동 문장으로 제시되어야 한다.

### **Task**

- 보고서 템플릿 구성
- 요약 작성
- 기술 및 경쟁사 비교 작성
- 전략적 시사점 도출
- reference 연결
- PDF 저장

### **Control Strategy**

- raw_content 직접 참조를 우선한다.
- key_points만 기반으로 보고서를 쓰지 않는다.
- unresolved가 많은 경우 경고를 포함하거나 상위 단계 재검토를 요청할 수 있다.
- canonical report output 계약은 `service-spec.md`를 따른다.

### **Structure**

- **Report Synthesis Stage**
- Strategy Report Generation Agent

---

## **11. 최종 검토 및 종료 승인 단계**

### **Goal**

최종 산출물이 정의된 품질 기준을 충족하는지 확인하고, 결과물을 종료 상태로 승인한다.

### **Criteria**

- 보고서 6개 목차 충족
- reference trace 가능
- priority matrix 포함
- unresolved/conflict 항목 명시
- PDF 산출 완료

### **Task**

- 최종 체크리스트 검토
- 보고서 품질 확인
- 종료 승인 또는 보완 요청

### **Control Strategy**

- Supervisor가 최종 승인권을 가진다.
- 미충족 시 필요한 단계만 부분 재진입시킨다.
- 전체 재실행은 하지 않는다.
- final review 보조 로직이 있더라도 승인 결정은 Supervisor가 기록한다.

### **Structure**

- **Final Approval Stage**
- Supervisor-controlled closing stage

---

# **한 번에 보는 큰 Workflow**

1. User Query 입력
2. Supervisor 초기화 및 실행 계획 수립
3. 병렬 검색
4. 검색 결과 정규화 및 적재
5. 전역 품질 검증
6. 재탐색 및 보완
7. 기술 성숙도 분석
8. 위협 수준 분석
9. 병합 및 우선순위 매트릭스 생성
10. 기술 전략 보고서 생성
11. 최종 검토 및 종료 승인

---
