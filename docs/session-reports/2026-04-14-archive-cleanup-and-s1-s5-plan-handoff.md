# 세션 인수인계 — archive 태그 정리 + S1~S5 튜닝 플랜 초안

## 개요

2026-04-14 세션. 직전 handoff ([2026-04-14-carry3-closure-handoff.md](2026-04-14-carry3-closure-handoff.md)) 의 `[unresolved]` 유일 항목인 archive 태그 정리와, `[next]` 2순위였던 S1~S5 튜닝 플랜 초안까지 동일 세션에서 완결.

## 작업 내역

### 1. archive/*-2026-04-11 원격 태그 44건 일괄 삭제

- 원격 `archive/*-2026-04-11` 패턴 태그 전량 (44건) `git push origin --delete` 로 제거
- 로컬 태그도 `git tag -d` 로 동기 정리
- main 히스토리 무손상 확인 (squash merge 로 코드는 이미 반영됨)
- 잔여 `archive/*-2026-04-11` 원격 태그: 0건

### 2. S1~S5 warn 과다 발동 튜닝 플랜 초안 작성

파일: [docs/plans/2026-04-14-s1-s5-warn-tuning.md](../plans/2026-04-14-s1-s5-warn-tuning.md)

핵심 설계 내용:
- 옵션 A (권장): `signoff_*/evaluate/skprompt.txt` §4 "판단 애매 조항" 을 허용형 → 제한형으로 재작성. warnings 트리거를 명시된 케이스만 허용
- 옵션 B: `info` 레벨 신설 — 스키마·UI 3축 수정 필요, 회귀 범위 큼
- 옵션 C: 루브릭 완화 — 비권장
- 구현 PR 은 별도 세션. 선행 조건: 147건의 최종 grade 분포와 warn/issue 공존 여부 재조사

## 수정 파일

| 파일 | 변경 |
|------|------|
| `docs/plans/2026-04-14-s1-s5-warn-tuning.md` | 신규 (S1~S5 튜닝 설계 초안) |
| `docs/session-reports/2026-04-14-archive-cleanup-and-s1-s5-plan-handoff.md` | 신규 (본 문서) |

코드 변경 없음. git 태그 삭제 + 문서 2건 추가.

## 직전 handoff `[unresolved]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| LOW (carry:2) archive/*-2026-04-11 원격 태그 정리 | **resolved** | 이번 세션에서 44건 전량 삭제 완료, 원격 잔여 0건 확인 |

직전 handoff 의 unresolved 항목이 완전히 해소되어 carry 이월 없음.

## 다음 세션 인수 요약

1. S1~S5 튜닝 플랜 실행 — 구현 PR 을 열기 전에 프로덕션 147건의 최종 grade 분포 재조사 (A/B/C 비율, warn/issue 공존 케이스)
2. 재조사 결과가 옵션 A 적용 조건에 부합하면 `backend/prompts/signoff_*/evaluate/skprompt.txt` 4개 파일의 §4 조항 개정 PR
3. content_filter / final summary 실측 경로 설계 (carry:3 closure 에서 CLOSED-POLICY 처리됨, 재개 시 Azure App Insights 접근 설계부터)

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-14-carry3-closure-handoff.md

[unresolved]
(없음 — 직전 handoff 의 archive 태그 정리 항목이 이번 세션에서 해소되어 이월 없음)

[decisions]
- CLOSED archive/*-2026-04-11 원격 태그 정리 — 44건 전량 삭제 완료, 원격 잔여 0건. main 히스토리 무손상 (squash merge 로 코드 이미 반영)
- S1~S5 warn 튜닝 설계: 옵션 A(프롬프트 warnings 기준 엄격화) 권장. 옵션 B(info 레벨 신설)는 스키마·UI 3축 수정으로 회귀 범위 큼
- S1~S5 튜닝 구현 PR 전 선행 조사 필요: 147건의 최종 grade 분포(A/B/C)와 warn/issue 동일 코드 공존 여부

[next]
1. 147건 rejection 로그 재조사 — grade 분포 + warn/issue 공존 여부 (Azure 로그 30일 보존 한계 고려, 가능한 빨리)
2. 재조사 결과에 따라 signoff_*/evaluate/skprompt.txt 4개 프롬프트 개정 PR (옵션 A 경로)
3. (선택) content_filter / final summary 실측 경로 설계 — Azure App Insights 접근 방법부터

[traps]
- /api/v1/logs?type=rejections 스키마가 "warnings 포함 로그" 인지 "issues 있는 로그만" 인지 불명확 — 147건 warn 55% 수치의 해석이 이 답에 좌우됨
- signoff skprompt 수정 시 _FORCED_HIGH_CODES (SEC*·RJ*) 는 엔진이 강제 high 처리 → 프롬프트 튜닝 범위에서 제외해야 회귀 방지
- 옵션 A 프롬프트 수정은 Azure OpenAI 평가 일관성에 영향 — 배포 전 브랜치 revert 경로 준비 필수
- Azure 로그 ts 보존 ~30일이므로 튜닝 전/후 비교는 동일 30일 윈도우에서 측정해야 bias 없음
CLAUDE_HANDOFF_END -->
