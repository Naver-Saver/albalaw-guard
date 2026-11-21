import { Icon } from '../components/common/Icon'
import { Badge } from '../components/common/Status'
import { ButtonLink } from '../components/common/ButtonLink'

const steps = [
  { icon: 'upload', title: '문서 사진을 올려요', text: '근로계약서나 급여명세서를 준비해 주세요.' },
  { icon: 'edit', title: '읽어낸 내용을 확인해요', text: '시급과 근무시간이 맞는지 직접 수정할 수 있어요.' },
  { icon: 'shield', title: '근거와 함께 살펴봐요', text: '확인이 필요한 항목과 공식 안내를 함께 확인해요.' },
] as const

export function LandingPage() {
  return <div className="landing">
    <section className="landing-hero" aria-labelledby="landing-title">
      <div className="landing-hero__copy"><div className="hero-kicker"><span aria-hidden="true" />처음 일하는 마음 곁에, Saver</div>
        <h1 id="landing-title">내 첫 알바,<br />작은 약속까지<br /><span>Saver와 확인해요.</span></h1>
        <p className="hero-description">어려운 근로계약서와 급여명세서,<br className="desktop-break" /> 혼자 고민하지 마세요.<br />내가 이해하는 언어로 차근차근 살펴볼 수 있어요.</p>
        <div className="hero-actions"><ButtonLink href="#/workspace">서비스 이용하기</ButtonLink><ButtonLink variant="secondary" href="#/guide"><Icon name="info" width="18" height="18" />소개 영상 보기</ButtonLink></div>
        <p className="hero-privacy"><Icon name="shield" width="16" height="16" />문서 원본은 처리 후 보관하지 않는 것을 원칙으로 해요.</p>
      </div>
      <div className="document-scene" role="img" aria-label="서비스 이용 예시: 근로계약서에서 시급과 근무시간을 확인하고 직접 수정하는 화면">
        <span className="scene-orbit scene-orbit--one" /><span className="scene-orbit scene-orbit--two" />
        <div className="document-paper"><div className="paper-top"><span>나의 첫 출근</span><span>SAVER</span></div><h2>근로계약서</h2><p className="paper-subtitle">함께 확인하는 나의 근로조건</p>
          <div className="paper-rule" /><div className="paper-row"><span>계약 기간</span><i /></div><div className="paper-row paper-row--selected"><span>시급</span><strong>직접 확인해 주세요</strong><span className="paper-cursor"><Icon name="check" width="15" height="15" /></span></div><div className="paper-row"><span>근무시간</span><i /></div><div className="paper-row"><span>휴게시간</span><i /></div><div className="paper-lines"><i /><i /><i /></div><div className="paper-signature">소중한 약속, 꼼꼼하게.</div>
        </div>
        <div className="scene-note"><span className="scene-note__icon"><Icon name="edit" /></span><div><strong>읽어낸 내용을 직접 확인해요</strong><p>잘못 읽힌 부분은 수정할 수 있어요.</p></div></div>
        <div className="scene-badge"><Icon name="shield" width="18" height="18" />공식 근거와 함께</div><span className="scene-example">이해를 돕기 위한 화면 예시</span>
      </div>
    </section>
    <section className="how-it-works" aria-labelledby="steps-title"><div className="section-heading"><div><p className="eyebrow">HOW IT WORKS</p><h2 id="steps-title">복잡한 문서도, 한 단계씩</h2></div><Badge tone="success">사진 한 장으로 시작</Badge></div><ol className="steps-grid">{steps.map((step, index) => <li key={step.title}><span className="step-icon"><Icon name={step.icon} width="23" height="23" /></span><div><span className="step-label">STEP 0{index + 1}</span><h3>{step.title}</h3><p>{step.text}</p></div></li>)}</ol></section>
    <div className="landing-bottom"><Icon name="chat" width="21" height="21" /><p>알고 싶은 부분은 편하게 질문하고, 대화 기록도 함께 정리해 보세요.</p><a href="#/guide">이용 방법 알아보기</a></div>
  </div>
}
