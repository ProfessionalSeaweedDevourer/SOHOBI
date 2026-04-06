import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { AnimatedBackground } from '../components/AnimatedBackground';
import { ThemeToggle } from '../components/ThemeToggle';
import { MessageSquare, FileText, Shield, AlertTriangle, Globe, Users, Lock, RefreshCw, Mail, ArrowLeft } from 'lucide-react';
import { motion } from 'motion/react';

const part1Articles = [
  {
    num: '제1조',
    title: '개인정보의 처리 목적',
    icon: Shield,
    color: 'var(--brand-blue)',
    content: (
      <>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          SOHOBI(이하 '서비스')는 F&B 분야 1인 창업자 및 소규모 사업자의 운영 효율 향상을 위한 멀티 에이전트 플랫폼으로서,
          아래의 목적을 위해 최소한의 범위 내에서 개인정보를 처리합니다.
        </p>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-semibold mb-1">1.1 AI 에이전트 기능 제공 및 정확도 향상</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>F&B 창업자 대상 상권 분석·재무 시뮬레이션·법령 안내·행정 절차 지원 등 핵심 에이전트 기능의 응답 생성</li>
              <li>생성형 AI의 환각(Hallucination) 현상 완화 및 최종 검증 에이전트의 품질 개선</li>
              <li>이용자의 업종·지역 맥락에 맞는 맞춤형 응답 최적화</li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold mb-1">1.2 서비스 운영 및 보안</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>서비스 이용 현황 분석 및 장애 대응</li>
              <li>부정 이용(프롬프트 인젝션 등) 탐지 및 보안 취약점 모니터링</li>
              <li>법령상 의무 이행 및 분쟁 해결</li>
            </ul>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제2조',
    title: '개인정보 처리의 적법 근거',
    icon: FileText,
    color: 'var(--brand-teal)',
    content: (
      <>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold mb-2">2.1 계약 이행 (개인정보 보호법 제15조 제1항 제4호)</p>
            <p className="text-sm text-muted-foreground leading-relaxed mb-2">
              이용자가 요청한 상권 분석·재무 시뮬레이션·법령 안내 등 AI 에이전트 서비스를 제공하기 위해
              대화 이력·세션 정보를 처리합니다. 로그인 회원의 경우 Google 계정 정보(이름·이메일·식별자)도
              서비스 제공을 위한 계약 이행 근거로 처리됩니다.
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold mb-2">2.2 정당한 이익 (개인정보 보호법 제15조 제1항 제6호)</p>
            <p className="text-sm text-muted-foreground leading-relaxed mb-2">
              서비스 보안 및 어뷰징 탐지(IP 주소 수집·분석, 프롬프트 인젝션 모니터링)는
              서비스 안정 운영이라는 <strong>정당한 이익</strong>을 법적 근거로 합니다.
              이 이익은 이용자의 사생활 침해 위험보다 우선하며, 수집된 IP는 보안 목적으로만 활용됩니다.
            </p>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제3조',
    title: '수집하는 개인정보 항목 및 보유 기간',
    icon: Lock,
    color: 'var(--brand-blue)',
    content: (
      <>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/20">
                <th className="text-left py-2 pr-4 font-semibold">구분</th>
                <th className="text-left py-2 pr-4 font-semibold">항목</th>
                <th className="text-left py-2 font-semibold">보유 기간</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b border-white/10">
                <td className="py-2 pr-4">비회원 서비스 이용</td>
                <td className="py-2 pr-4">대화 이력, 에이전트 요청 내역, 세션 ID</td>
                <td className="py-2">24시간</td>
              </tr>
              <tr className="border-b border-white/10">
                <td className="py-2 pr-4">로그인 회원 서비스 이용</td>
                <td className="py-2 pr-4">대화 이력, 에이전트 요청 내역, 세션 ID, Google 계정명·이메일·식별자</td>
                <td className="py-2">30일 (탈퇴 요청 시 즉시 삭제)</td>
              </tr>
              <tr className="border-b border-white/10">
                <td className="py-2 pr-4">자동 수집 (전체)</td>
                <td className="py-2 pr-4">서비스 접속 로그, IP 주소 (보안·어뷰징 탐지 목적)</td>
                <td className="py-2">6개월</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 text-red-400 font-semibold">수집 금지</td>
                <td className="py-2 pr-4 text-red-400">주민등록번호, 계좌번호, 여권번호 등 고유식별정보</td>
                <td className="py-2 text-red-400 font-semibold">수집하지 않습니다</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="glass rounded-xl p-4 border border-yellow-400/30 bg-yellow-400/5">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-yellow-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-muted-foreground leading-relaxed">
              <strong className="text-yellow-400">주의</strong>: 이용자가 프롬프트에 직접 입력한 민감정보(고유식별정보 포함)는
              당사가 의도적으로 수집하지 않으나, 입력된 경우 시스템에 일시적으로 처리될 수 있습니다.
              <strong> 민감정보를 프롬프트에 입력하지 마십시오.</strong>
            </p>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제4조',
    title: '개인정보의 안전성 확보 조치',
    icon: Shield,
    color: 'var(--brand-teal)',
    content: (
      <>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold mb-2">4.1 입출력 필터링 시스템</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li><strong>입력 단계</strong>: 개인정보 패턴(전화번호, 이메일 등) 및 프롬프트 인젝션 공격 자동 탐지</li>
              <li><strong>출력 단계</strong>: 생성된 응답 내 개인정보 노출 여부 검토 및 필터링</li>
              <li>최종 검증 에이전트를 통한 루브릭 기반 출력 품질 검사</li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold mb-2">4.2 인프라 보안</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Azure 환경 내 HTTPS 암호화 통신 적용</li>
              <li>Azure Cosmos DB 및 Azure Blob Storage 접근 권한 최소화 (Role-Based Access Control)</li>
              <li>API 키·시크릿 정보는 Azure Key Vault를 통해 관리하며 소스코드 하드코딩 금지</li>
            </ul>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제5조',
    title: '정보주체의 권리 및 행사 방법',
    icon: Users,
    color: 'var(--brand-blue)',
    content: (
      <>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/20">
                <th className="text-left py-2 pr-4 font-semibold">권리 종류</th>
                <th className="text-left py-2 pr-4 font-semibold">내용</th>
                <th className="text-left py-2 font-semibold">행사 방법</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              {[
                ['열람 요청', '본인의 개인정보 처리 현황 확인', '고객 지원 이메일 접수'],
                ['정정·삭제 요청', '부정확한 정보 수정 또는 삭제', '고객 지원 이메일 접수 후 10일 이내 조치'],
                ['처리 정지 요청', '개인정보 처리 중단 요청', '고객 지원 이메일 접수 후 10일 이내 조치'],
                ['데이터 삭제 요청', '보유 중인 대화 이력·세션 데이터 즉시 삭제 요청', '고객 지원 이메일 접수 후 10일 이내 조치'],
              ].map(([right, desc, method], i) => (
                <tr key={i} className="border-b border-white/10">
                  <td className="py-2 pr-4 font-medium">{right}</td>
                  <td className="py-2 pr-4">{desc}</td>
                  <td className="py-2">{method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="glass rounded-xl p-4 border border-blue-400/30 bg-blue-400/5">
          <div className="flex items-start gap-2">
            <Shield size={16} className="text-[var(--brand-blue)] mt-0.5 flex-shrink-0" />
            <p className="text-sm text-muted-foreground leading-relaxed">
              삭제 요청 접수 후 10일 이내에 대화 이력 및 세션 데이터를 삭제합니다.
              단, 법령상 보존 의무가 있는 접속 로그는 해당 의무 기간(6개월) 경과 후 삭제됩니다.
            </p>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제6조',
    title: '개인정보의 국외 이전 및 수탁 업체',
    icon: Globe,
    color: 'var(--brand-teal)',
    content: (
      <>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          본 서비스는 글로벌 클라우드 인프라를 활용함에 따라 일부 개인정보가 해외로 이전될 수 있습니다.
        </p>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm border-collapse">
            <tbody className="text-muted-foreground">
              {[
                ['이전 국가', '미국 (Azure East US 2 리전)'],
                ['국내 처리', '대한민국 (Azure Korea Central 리전) — 핵심 백엔드 서비스'],
                ['수탁 업체', 'Microsoft Corporation'],
                ['이전 목적', '서비스 데이터 저장·처리, 생성형 AI API 연동 (Azure AI Foundry)'],
                ['이전 항목', '서비스 이용 로그, 대화 이력 (암호화 전송)'],
                ['보호 조치', 'Microsoft 표준 계약 조항(SCC) 및 데이터 보호 부속 계약(DPA) 적용'],
              ].map(([label, value], i) => (
                <tr key={i} className="border-b border-white/10">
                  <td className="py-2 pr-4 font-semibold w-32">{label}</td>
                  <td className="py-2">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="glass rounded-xl p-4 border border-blue-400/30 bg-blue-400/5">
          <div className="flex items-start gap-2">
            <Globe size={16} className="text-[var(--brand-blue)] mt-0.5 flex-shrink-0" />
            <p className="text-sm text-muted-foreground leading-relaxed">
              핵심 백엔드 서비스는 국내(Azure Korea Central) 리전에서 운영되며,
              일부 보조 서비스 및 AI 추론 기능은 미국(Azure East US 2) 리전을 경유할 수 있습니다.
            </p>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제7조',
    title: '개인정보 처리방침 변경',
    icon: RefreshCw,
    color: 'var(--brand-blue)',
    content: (
      <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside leading-relaxed">
        <li>본 처리방침은 법령 개정 또는 서비스 변경 시 업데이트될 수 있습니다.</li>
        <li>변경 사항은 시행 7일 전 서비스 공지사항을 통해 사전 안내합니다.</li>
        <li>중요한 권리 관련 변경은 서비스 접속 시 별도 팝업 안내를 병행합니다.</li>
      </ul>
    ),
  },
  {
    num: '제8조',
    title: '개인정보 보호책임자',
    icon: Mail,
    color: 'var(--brand-teal)',
    content: (
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <tbody className="text-muted-foreground">
            {[
              ['책임자', 'SOHOBI 서비스 운영팀'],
              ['연락처', 'support@sohobi.kr'],
              ['문의 처리', '접수 후 영업일 기준 3일 이내 회신'],
            ].map(([label, value], i) => (
              <tr key={i} className="border-b border-white/10">
                <td className="py-2 pr-4 font-semibold w-28">{label}</td>
                <td className="py-2">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ),
  },
];

const part2Articles = [
  {
    num: '제1조',
    title: 'AI 생성 콘텐츠의 기술적 한계',
    icon: AlertTriangle,
    color: 'var(--brand-orange)',
    content: (
      <>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold mb-2">1.1 정확성 미보장</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>사실과 다른 정보(환각, Hallucination)를 생성할 수 있으며, 이는 생성형 AI의 본질적 특성입니다.</li>
              <li>법령·세무·위생 기준 등 시시각각 변동하는 정보는 최신 상태를 보장하지 않습니다.</li>
              <li>특정 지역·업종에 국한된 세부 규정은 실제와 다를 수 있습니다.</li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold mb-2">1.2 전문가 확인 권고</p>
            <div className="glass rounded-xl p-4 border border-yellow-400/30 bg-yellow-400/5 mb-2">
              <div className="flex items-start gap-2">
                <AlertTriangle size={16} className="text-yellow-400 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  <strong className="text-yellow-400">중요</strong>: F&B 관련 사업자 등록, 위생 법규, 세무 신고, 임대차 계약 등 중요 의사결정 시에는
                  반드시 공인 회계사·세무사·변호사 등 해당 분야 전문가의 별도 자문을 받으시기 바랍니다.
                  <strong> SOHOBI의 응답은 참고 자료로만 활용하십시오.</strong>
                </p>
              </div>
            </div>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>SOHOBI는 법무·세무·의료 등 전문 자격이 요구되는 분야의 공식 서비스를 대체하지 않습니다.</li>
              <li>서비스 내 정보를 근거로 한 최종 의사결정의 책임은 이용자 본인에게 있습니다.</li>
            </ul>
          </div>
        </div>
      </>
    ),
  },
  {
    num: '제2조',
    title: '허용되는 이용방침 (AUP)',
    icon: Shield,
    color: 'var(--brand-blue)',
    content: (
      <>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          이용자는 서비스를 합법적이고 선의의 목적으로만 사용해야 하며, 다음의 행위는 엄격히 금지됩니다.
        </p>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/20">
                <th className="text-left py-2 pr-4 font-semibold">금지 행위 유형</th>
                <th className="text-left py-2 font-semibold">구체적 예시</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              {[
                ['개인정보 침해', '타인의 성명·연락처·계좌번호 등을 무단 입력하거나 추출을 시도하는 행위'],
                ['보안 우회 시도', '프롬프트 인젝션, 시스템 프롬프트 유출 시도, 모델 탈옥(Jailbreak) 시도'],
                ['유해 콘텐츠 유도', '불법 약물·무기 제조, 범죄 행위, 혐오 콘텐츠 생성을 유도하는 행위'],
                ['허위 정보 유포', 'AI 응답을 의도적으로 왜곡하거나 허위 정보를 확산시키는 행위'],
                ['서비스 남용', '자동화 프로그램을 이용한 대량 요청, 서비스 인프라 과부하 유발'],
              ].map(([type, example], i) => (
                <tr key={i} className="border-b border-white/10">
                  <td className="py-2 pr-4 font-medium text-red-400">{type}</td>
                  <td className="py-2">{example}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-muted-foreground">
          위 금지 행위 발생 시 서비스는 사전 통보 없이 해당 이용을 제한하거나 법적 조치를 취할 수 있습니다.
        </p>
      </>
    ),
  },
  {
    num: '제3조',
    title: '이용자 책임 및 손해배상',
    icon: FileText,
    color: 'var(--brand-teal)',
    content: (
      <div className="space-y-4">
        <div>
          <p className="text-sm font-semibold mb-2">3.1 입력 데이터에 대한 책임</p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>이용자가 프롬프트에 직접 입력한 정보의 정확성 및 적법성에 대한 책임은 이용자 본인에게 있습니다.</li>
            <li>이용자 본인 또는 제3자의 민감정보를 프롬프트에 입력하여 발생하는 모든 손해는 이용자가 부담합니다.</li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold mb-2">3.2 AI 결과물 활용에 대한 책임</p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>SOHOBI가 생성한 콘텐츠를 실제 사업 운영·투자·법적 판단 등에 적용하여 발생하는 결과에 대해, 서비스 제공자는 고의 또는 중대한 과실이 없는 한 민·형사상 책임을 지지 않습니다.</li>
            <li>AI 응답을 기반으로 체결한 계약, 제출한 서류, 집행한 투자 등으로 인한 손실에 대해 서비스는 보상 의무를 지지 않습니다.</li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold mb-2">3.3 서비스 가용성</p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>서비스는 Azure 클라우드 인프라 장애, 정기 점검, 천재지변 등으로 인해 일시 중단될 수 있으며, 이로 인한 손해에 대해 책임을 지지 않습니다.</li>
            <li>생성형 AI 모델 업데이트로 인해 응답 형식·내용이 변경될 수 있습니다.</li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    num: '제4조',
    title: '지식재산권',
    icon: Lock,
    color: 'var(--brand-blue)',
    content: (
      <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside leading-relaxed">
        <li>서비스의 UI, 에이전트 로직, 브랜드 자산(SOHOBI)은 서비스 제공자의 지식재산입니다.</li>
        <li>이용자가 서비스를 통해 생성한 응답 결과물의 지식재산권은 이용자에게 귀속되나, 서비스 개선 목적의 비식별 활용에 동의한 것으로 봅니다.</li>
        <li>이용자는 서비스 내 콘텐츠를 상업적 목적으로 무단 재판매하거나 경쟁 서비스 구축에 활용할 수 없습니다.</li>
      </ul>
    ),
  },
  {
    num: '제5조',
    title: '분쟁 해결 및 관할',
    icon: Globe,
    color: 'var(--brand-teal)',
    content: (
      <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside leading-relaxed">
        <li>본 약관에 관한 분쟁은 대한민국 법률을 준거법으로 하며, 서울중앙지방법원을 1심 관할법원으로 합니다.</li>
        <li>분쟁 발생 시 우선 고객 지원 채널을 통한 협의를 시도하며, 협의가 불가한 경우 법원에 의뢰합니다.</li>
      </ul>
    ),
  },
];

function ArticleCard({ article, index }) {
  const Icon = article.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.05 }}
      className="group"
    >
      <div className="glass rounded-2xl p-8 shadow-elevated transition-glow hover-lift relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
          style={{ backgroundColor: article.color }}
        />
        <div className="flex items-start gap-4 mb-6">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 relative"
            style={{ backgroundColor: `${article.color}15` }}
          >
            <div
              className="absolute inset-0 rounded-xl blur-xl opacity-30 group-hover:opacity-50 transition-opacity"
              style={{ backgroundColor: article.color }}
            />
            <Icon size={20} style={{ color: article.color }} className="relative z-10" />
          </div>
          <div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full mb-1 inline-block" style={{ backgroundColor: `${article.color}15`, color: article.color }}>
              {article.num}
            </span>
            <h3 className="text-lg font-semibold leading-snug">{article.title}</h3>
          </div>
        </div>
        <div className="relative z-10">{article.content}</div>
      </div>
    </motion.div>
  );
}

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <motion.div
              className="w-10 h-10 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-xl flex items-center justify-center shadow-lg relative"
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <div className="absolute inset-0 bg-[var(--brand-blue)] rounded-xl blur-lg opacity-40" />
              <MessageSquare size={24} className="text-white relative z-10" />
            </motion.div>
            <div>
              <h1 className="text-xl leading-none mb-0.5 gradient-text">SOHOBI</h1>
              <p className="text-xs text-muted-foreground">소호비</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/user">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button variant="outline" size="sm" className="glass border shadow-lg">
                  AI 상담 →
                </Button>
              </motion.div>
            </Link>
            <Link to="/">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button variant="outline" className="glass border shadow-lg gap-1.5">
                  <ArrowLeft size={16} />
                  홈으로
                </Button>
              </motion.div>
            </Link>
          </div>
        </div>
      </motion.header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-20 md:py-28">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-8 shadow-elevated"
          >
            <FileText size={16} className="text-[var(--brand-blue)]" />
            <span className="gradient-text font-semibold">법적 고지</span>
          </motion.div>

          <motion.h1
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-4xl md:text-5xl lg:text-6xl mb-6 leading-tight tracking-tight gradient-text"
          >
            개인정보처리방침
          </motion.h1>

          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-base md:text-lg text-muted-foreground leading-relaxed"
          >
            버전 1.0 · 시행일 2025년 4월
          </motion.p>
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="text-sm text-muted-foreground mt-3 max-w-2xl mx-auto leading-relaxed"
          >
            본 문서는 개인정보 보호법 및 생성형 AI 서비스 관련 안내서를 준거로 작성된 SOHOBI 서비스의 공식 개인정보처리방침 및 이용방침입니다.
          </motion.p>
        </div>
      </section>

      {/* Part 1 */}
      <section className="container mx-auto px-4 pb-20">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm mb-4 shadow-elevated">
              <Shield size={14} className="text-[var(--brand-blue)]" />
              <span className="text-muted-foreground">제1부</span>
            </div>
            <h2 className="text-3xl md:text-4xl gradient-text">개인정보처리방침</h2>
          </motion.div>

          <div className="space-y-6">
            {part1Articles.map((article, idx) => (
              <ArticleCard key={article.num} article={article} index={idx} />
            ))}
          </div>
        </div>
      </section>

      {/* Part 2 */}
      <section className="container mx-auto px-4 pb-20">
        <div className="max-w-4xl mx-auto">
          <div className="border-t border-white/20 mb-16" />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm mb-4 shadow-elevated">
              <AlertTriangle size={14} className="text-[var(--brand-orange)]" />
              <span className="text-muted-foreground">제2부</span>
            </div>
            <h2 className="text-3xl md:text-4xl gradient-text">면책조항 및 이용방침</h2>
          </motion.div>

          <div className="space-y-6">
            {part2Articles.map((article, idx) => (
              <ArticleCard key={article.num + '-p2'} article={article} index={idx} />
            ))}
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section className="container mx-auto px-4 pb-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-2xl mx-auto"
        >
          <div className="glass rounded-3xl p-10 text-center shadow-elevated-lg relative overflow-hidden">
            <div
              className="absolute inset-0 bg-gradient-to-r from-[var(--brand-blue)] via-[var(--brand-teal)] to-[var(--brand-blue)] opacity-10 animate-shimmer"
              style={{ backgroundSize: '200% 100%' }}
            />
            <div className="absolute top-0 left-1/4 w-48 h-48 bg-[var(--brand-blue)] rounded-full blur-3xl opacity-20 animate-float" />
            <div className="relative z-10">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg relative" style={{ backgroundColor: 'var(--brand-blue)15' }}>
                <div className="absolute inset-0 rounded-2xl blur-xl opacity-30" style={{ backgroundColor: 'var(--brand-blue)' }} />
                <Mail size={28} style={{ color: 'var(--brand-blue)' }} className="relative z-10" />
              </div>
              <h2 className="text-2xl md:text-3xl mb-3 gradient-text">개인정보 관련 문의</h2>
              <p className="text-muted-foreground mb-2">
                <a href="mailto:support@sohobi.kr" className="hover:text-[var(--brand-blue)] transition-colors font-medium underline underline-offset-2">
                  support@sohobi.kr
                </a>
              </p>
              <p className="text-sm text-muted-foreground">접수 후 영업일 기준 3일 이내 회신</p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="glass border-t border-white/20 py-12 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p className="mb-2">© 2026 SOHOBI.</p>
          <p className="mb-3">소상공인을 위한 AI 컨설팅 플랫폼</p>
          <Link to="/privacy" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
            개인정보처리방침
          </Link>
          <p className="text-xs text-muted-foreground text-center mt-4">
            시행일: 2026년 4월 7일 &nbsp;|&nbsp; 버전: 1.1
          </p>
        </div>
      </footer>
    </div>
  );
}
