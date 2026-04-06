# 업데이트 로그 (Changelog) 페이지 추가 계획

## Context

SOHOBI는 개발 속도가 매우 빠른 프로젝트로, 사용자가 이 역동성을 직접 느낄 수 있도록 GitHub 커밋 기록을 자동으로 불러와 표시하는 `/changelog` 페이지를 추가한다.

---

## 기술 결정

- **데이터 소스**: GitHub 공개 API (`https://api.github.com/repos/ProfessionalSeaweedDevourer/SOHOBI/commits`)
- **캐싱**: localStorage, TTL 1시간 (페이지별 키 `sohobi_changelog_cache_p{N}`)
- **데이터 로딩**: 초기 100개 + "더 보기" 버튼으로 페이지네이션
- **필터링**: 커밋 타입별 (feat/fix/docs 등), useMemo로 반응형 처리

---

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `frontend/src/pages/Changelog.jsx` | **신규 생성** (메인 작업) |
| `frontend/src/App.jsx` | `/changelog` 라우트 추가 |
| `frontend/src/pages/Landing.jsx` | 푸터에 "업데이트 로그" 링크 추가 (line 255-257) |
| `frontend/src/pages/Home.jsx` | 하단에 "업데이트 로그" 링크 추가 |

---

## Changelog.jsx 구조

### 상수

```js
const CACHE_TTL_MS = 60 * 60 * 1000; // 1시간

const TYPE_MAP = {
  feat:     { label: "새 기능",   color: "#0891b2" },
  fix:      { label: "버그 수정", color: "#ef4444" },
  docs:     { label: "문서",      color: "#8b5cf6" },
  chore:    { label: "유지보수",  color: "#717182" },
  refactor: { label: "리팩토링", color: "#f97316" },
  perf:     { label: "성능",      color: "#14b8a6" },
  test:     { label: "테스트",    color: "#eab308" },
  ci:       { label: "CI/CD",     color: "#6366f1" },
  security: { label: "보안",      color: "#ec4899" },
};
```

### 핵심 유틸 함수

```js
// 캐싱 포함 GitHub API fetch
async function fetchCommits(page = 1) {
  const cacheKey = `sohobi_changelog_cache_p${page}`;
  try {
    const raw = localStorage.getItem(cacheKey);
    if (raw) {
      const { fetchedAt, commits } = JSON.parse(raw);
      if (Date.now() - new Date(fetchedAt).getTime() < CACHE_TTL_MS)
        return commits;
    }
  } catch (_) {}
  const url = `https://api.github.com/repos/ProfessionalSeaweedDevourer/SOHOBI/commits?per_page=100&page=${page}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  const commits = await res.json();
  localStorage.setItem(cacheKey, JSON.stringify({ fetchedAt: new Date().toISOString(), commits }));
  return commits;
}

// 커밋 파싱 (conventional commit → type + message)
function parseCommit(raw) {
  const firstLine = raw.commit.message.split("\n")[0].trim();
  const match = firstLine.match(/^(\w+)(?:\([^)]+\))?:\s*(.+)$/);
  const type = match ? match[1].toLowerCase() : "other";
  return {
    sha: raw.sha, shortSha: raw.sha.slice(0, 7),
    type, message: match ? match[2] : firstLine,
    date: raw.commit.author.date, author: raw.commit.author.name,
    url: raw.html_url,
    typeMeta: TYPE_MAP[type] ?? { label: type, color: "#717182" },
  };
}

// 날짜별 그룹핑 (최신순)
function groupByDate(commits) {
  const map = new Map();
  for (const c of commits) {
    const key = c.date.slice(0, 10);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(c);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, commits]) => ({
      dateKey: key,
      dateLabel: new Date(key + "T00:00:00").toLocaleDateString("ko-KR", {
        year: "numeric", month: "long", day: "numeric", weekday: "short"
      }),
      commits,
    }));
}

// 상대 시간 표시
function relativeTime(isoDate) {
  const d = Math.floor((Date.now() - new Date(isoDate)) / 86400000);
  if (d === 0) return "오늘";
  if (d === 1) return "어제";
  if (d < 7)  return `${d}일 전`;
  if (d < 30) return `${Math.floor(d / 7)}주 전`;
  return `${Math.floor(d / 30)}개월 전`;
}
```

### 컴포넌트 트리

```
Changelog
├── AnimatedBackground
├── motion.header (sticky, glass)
│   ├── Link "← 홈" → "/"
│   ├── SOHOBI 로고 + "업데이트 로그"
│   └── ThemeToggle
├── section: Hero
│   ├── GitCommit 아이콘 + "개발 히스토리" 배지 (glass, rounded-full)
│   ├── h1: "업데이트 <span gradient>로그</span>"
│   └── p: 부제목 + 커밋 수 표시
├── section: 필터 바
│   └── overflow-x-auto flex gap-2 → 타입별 버튼 (all + 실제 존재하는 타입만)
├── section: 타임라인
│   └── filteredGroups.map(DateGroup)
│       ├── 날짜 레이블 (text-xs text-muted-foreground mb-3)
│       └── commits.map(CommitCard)
│           ├── TypeBadge (색상 인라인 스타일)
│           ├── 커밋 메시지 텍스트
│           └── author + relativeTime + SHA 링크 (ExternalLink 아이콘)
├── LoadMore 버튼 (hasMore && !isLoading)
├── 로딩/에러 상태 UI
└── footer (glass, 저작권 + 링크들)
```

### 상태

```js
const [commits, setCommits] = useState([]);          // 파싱된 커밋 전체
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState(null);
const [currentPage, setCurrentPage] = useState(1);
const [hasMore, setHasMore] = useState(true);
const [activeFilter, setActiveFilter] = useState("all");

const groups = useMemo(() => groupByDate(commits), [commits]);
const filteredGroups = useMemo(() => {
  if (activeFilter === "all") return groups;
  return groups
    .map(g => ({ ...g, commits: g.commits.filter(c => c.type === activeFilter) }))
    .filter(g => g.commits.length > 0);
}, [groups, activeFilter]);
const availableTypes = useMemo(() => {
  const seen = new Set(groups.flatMap(g => g.commits.map(c => c.type)));
  return ["all", ...Object.keys(TYPE_MAP).filter(t => seen.has(t))];
}, [groups]);
```

---

## App.jsx 변경 (정확한 위치)

```jsx
// 상단 import 추가
import Changelog from "./pages/Changelog";

// line 31 앞에 라우트 추가
<Route path="/changelog" element={<Changelog />} />
```

---

## Landing.jsx 변경 (line 255-257)

```jsx
// 기존
<Link to="/privacy" ...>개인정보처리방침</Link>

// 변경 후
<Link to="/privacy" ...>개인정보처리방침</Link>
<span className="mx-2 opacity-30">·</span>
<Link to="/changelog" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
  업데이트 로그
</Link>
```

---

## Home.jsx 변경 (마지막 </div> 앞)

```jsx
<p className="mt-10 text-xs text-muted-foreground text-center">
  <Link to="/changelog" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
    업데이트 로그
  </Link>
  <span className="mx-2 opacity-30">·</span>
  <Link to="/privacy" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
    개인정보처리방침
  </Link>
</p>
```

---

## Lucide 아이콘 (추가 설치 불필요, 이미 사용 중)

`GitCommit`, `ExternalLink`, `RefreshCw`, `AlertCircle`, `ArrowLeft`, `Filter`

---

## 검증 방법

1. `cd frontend && npm run dev` 실행
2. `http://localhost:5173/changelog` 접속 → 커밋 목록 로딩 확인
3. 브라우저 DevTools → Application → localStorage → `sohobi_changelog_cache_p1` 키 존재 확인
4. 필터 버튼 클릭 → 해당 타입 커밋만 표시 확인
5. "더 보기" 버튼 → 추가 커밋 로딩 확인
6. Landing(`/`) 및 Home(`/home`) 푸터에 "업데이트 로그" 링크 노출 확인
7. 링크 클릭 시 `/changelog` 페이지로 이동 확인
