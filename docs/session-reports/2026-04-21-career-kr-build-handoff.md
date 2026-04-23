# 2026-04-21 경력기술서 국문 통합 빌드 세션 인수인계

## 요약

박주현 경력기술서 국문 2종(단독·통합) `.docx`·`.pdf` 4개 산출물을 `work/career/dist/`에 생성했다. GRIP 세션(2026-04-21) handoff-notes §4.2 기여범위 규정을 반영하여 VanWonen 섹션을 "개인 주도(Mistral 챗봇 단독) / 팀 공동(pdfminer.six ETL · LDA · SBERT 분류·대시보드 — Bryan 주저작)"로 재구조화했다. 원 지시문 §7-1의 "마크다운 수정 금지" 조항은 handoff-notes §6 "충돌 시 notes 우선" 규정으로 오버라이드됨. 산출물은 `work/` = gitignored 로컬 전용이며, 본 세션의 커밋 범위는 `.gitignore`에 `work/` 추가 한 줄.

## 브랜치 / PR

- **브랜치**: `chore/park-career-build-gitignore` (origin/main 기반)
- **PR**: [#324](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/324) OPEN — Test plan TC 2건 모두 PASS 코멘트 완료, admin merge 대기

## 수정 파일

| 경로 | 변경 | 용도 |
|---|---|---|
| `.gitignore` | +3 | 경력기술서 빌드 산출물 `work/` 디렉토리 추적 제외 |

커밋 내역은 `git log origin/main..chore/park-career-build-gitignore` 참조.

## 생성 산출물 (git 미추적, 로컬 전용)

`work/career/dist/` 하위:
- `박주현_경력기술서_단독_v1.docx` (2.5 MB)
- `박주현_경력기술서_단독_v1.pdf` (613 KB)
- `박주현_경력기술서_통합_v1.docx` (3.2 MB)
- `박주현_경력기술서_통합_v1.pdf` (1.0 MB)

최종 zip: `work/career-kr-v1-20260421.zip` (7.1 MB)

사용자 PASS 판정 완료. 줄 바꿈·폰트 세밀 조정은 사용자 수동 처리.

## 설치된 도구 (Homebrew)

- `pandoc` 3.9.0.2
- LibreOffice 26.2.2 (cask, `/Applications/LibreOffice.app/Contents/MacOS/soffice`)
- NanumGothic (Regular/Bold/ExtraBold, `~/Library/Fonts/`)

재빌드 명령은 `~/.claude/plans/handoff-sohobi-repo-integration-build-2-optimized-truffle.md` Phase 3~5 참조.

## 이전 handoff [unresolved] 재판정

| 이전 항목 | 판정 | 근거 |
|---|---|---|
| MED (carry:3) legal-index + gov-programs-index 원본 데이터 확보 | **carried → MED (carry:4)** | 본 세션 범위 밖. 이관 팀원 작업 대기 중. 외부 블로커이므로 내부 판단만으로 closure 불가 |
| MED (carry:1) Phase 2 sohobi-search-kr 실행 go/no-go | **carried → MED (carry:2)** | 본 세션 범위 밖. data/cost/quota gate 3건 여전히 미해결 |
| LOW (carry:3) placeholder 감지 가드 | **INVALIDATED** | 이전 handoff에서 "다음 carry 시 closure 재검토" 명시. carry:4에 도달하고도 실제 착수 없음. 공격 표면 0 + 4회 연속 deprioritize → 방어 가치 대비 시간 비용 불균형으로 영구 closure. 재주입 회귀 발생 시 신규 이슈로 open |

## 다음 세션 인수 요약

1. PR #324 admin merge 대기 (단순 gitignore 1줄 변경, TC PASS 완료)
2. **영문 버전은 별도 세션 권장** — 원 지시문 §Phase 8 §5. 직역 금지, reference.docx 템플릿 영문화, 캡션 영문 재작성 필요. 영문 Figure 2용 `assets/sohobi-signoff-performance-en.png` 이미 준비됨
3. 이전 세션 이월분: 이관 팀원의 원본 데이터 확보 진척 확인 → Phase 2 sohobi-search-kr 실행 trigger
4. 배너 관련 후속(복구 timeline 재평가, MaintenanceNotice 제거)은 이전 handoff 그대로 유효

---

<!-- CLAUDE_HANDOFF_START
branch: chore/park-career-build-gitignore
pr: 324
prev: 2026-04-20-maintenance-banner-and-phase2-plan-handoff.md

[unresolved]
- MED (carry:4) legal-index + gov-programs-index 원본 데이터 확보 — 외부 블로커(이관 팀원). closure 불가, 내부 대응 없음
- MED (carry:2) Phase 2 sohobi-search-kr 실행 go/no-go — data/cost/quota gate 3건 미해결

[decisions]
- CLOSED: 경력기술서 국문 2종 빌드 — work/career/dist/ 4파일 생성, 사용자 PASS 판정
- CLOSED: VanWonen 기여범위 재작성 — handoff-notes §4.2 반영, "개인 주도/팀 공동" 서브섹션 분리. 개인 주도 서브섹션 grep 검증 통과
- INVALIDATED: LOW placeholder 감지 가드 — carry:4 도달, 공격 표면 0 + 4회 deprioritize. 방어 가치 대비 시간 비용 불균형으로 영구 closure
- 원 지시문 "마크다운 수정 금지"와 handoff-notes "단독 표현 금지"의 충돌은 notes §6에 따라 notes 우선 — 재작성본은 work/career/ 에만 존재, handoff/ 원본은 보존
- 빌드 체인: pandoc 3.9 → LibreOffice headless → PDF. Korean 폰트는 NanumGothic cask + AppleGothic fallback
- Figure 5는 반드시 grip-figure-5-chatbot.png (챗봇 단일 패널). product.png는 Bryan 주저작 대시보드 포함이므로 개인 CV에 사용 금지 (notes §3.2)
- work/ 를 .gitignore에 추가 — 빌드 산출물은 로컬 전용, 필요 시 zip 개별 전달

[next]
1. PR #324 admin merge (사용자 지시 시)
2. 영문 버전 빌드는 별도 세션 — 직역 금지, reference.docx 영문화 + 캡션 재작성 필요. sohobi-signoff-performance-en.png 는 준비됨
3. 이관 팀원의 원본 데이터 확보 진척 확인 → Phase 2 sohobi-search-kr 실행 trigger
4. 약 1주 경과 시 복구 timeline 재평가 (이전 세션 이월)
5. 복구 완료 시 MaintenanceNotice.jsx 제거 (이전 세션 이월)

[traps]
- work/career/ 산출물의 docx 내부 이미지 폭은 pandoc `{width=XX%}` 속성으로 제어. 값을 바꿔도 docx에서는 무시되는 경우가 있음. reference.docx 의 Figure 스타일을 LibreOffice/Word 로 열어 수동 조정해야 할 수 있음
- 사용 기술 테이블 한글 폰트가 본문과 달라질 수 있음 (pandoc `--variable=mainfont` 표 불안정). LibreOffice로 Compact Grid 스타일 폰트를 NanumGothic으로 교체하면 해결
- handoff-notes 와 매니페스트가 상충하면 notes §6 에 따라 notes 우선. Figure 5 파일명(chatbot vs product)이 가장 자주 회귀 가능한 지점
- 영문 버전에서 Figure 5 캡션의 "solely developed by the author" 문구는 기여 경계 명시 핵심 장치 — 의역·축약 금지 (notes §3.3)
CLAUDE_HANDOFF_END -->
