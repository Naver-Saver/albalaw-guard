import { useState } from 'react'
import { Icon } from '../components/common/Icon'
import { ButtonLink } from '../components/common/ButtonLink'

type GuideVideo = { src: string; poster?: string; captions?: string }

const contractVideo: GuideVideo = {
  src: '/videos/contract-check.mp4',
  poster: '/videos/contract-check-poster.jpg',
  captions: '/videos/contract-check.ko.vtt',
}

const checklist = [
  { title: '시급·지급일·계산방법', text: '얼마를 받고, 언제 어떻게 받는지 확인하세요.' },
  { title: '근무요일·시간·휴게시간', text: '일하기로 한 요일과 시간, 쉬는 시간이 약속과 같은지 살펴보세요.' },
  { title: '빈칸은 확인하고 서명', text: '모르는 내용이나 빈칸은 설명을 듣고 채운 뒤 서명하세요.' },
  { title: '계약서, 나도 한 부', text: '작성한 계약서는 꼭 받아 보관하세요. 궁금한 점은 고용노동부 1350에 문의할 수 있어요.' },
]

export function GuidePage({ video = contractVideo }: { video?: GuideVideo }) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const videoReady = video?.src && failedSource !== video.src
  return <div className="guide-page">
    <div className="guide-heading"><p className="eyebrow">SAVER · LABOR RIGHTS</p><h1>알바 계약서, 서명 전 30초 체크</h1><p>근로계약서를 작성하기 전에 꼭 살펴볼 내용을 알아보세요.</p></div>
    <section className="guide-card" aria-label="근로계약서 작성 전 교육 영상">
      {videoReady ? <video key={video.src} src={video.src} className="guide-player" controls playsInline preload="metadata" poster={video.poster} onError={() => setFailedSource(video.src)}>
        {video.captions && <track kind="captions" src={video.captions} srcLang="ko" label="한국어" default />}영상 재생을 지원하지 않는 브라우저예요. 아래 계약서 체크리스트를 확인해 주세요.
      </video> : <div className="guide-placeholder"><span className="guide-placeholder__icon"><Icon name="file" width="32" height="32" /></span><span className="guide-placeholder__label">SAVER · 근로계약서 체크</span><h2>{video?.src ? '영상을 불러오지 못했어요' : '계약서 교육 영상을 준비 중이에요'}</h2><p>영상 대신 아래 네 가지를 먼저 확인해 보세요.</p><span className="guide-placeholder__tag">서명하기 전, 잠깐!</span></div>}
      <div className="guide-card__caption"><span>알바 계약서, 서명 전 30초 체크</span><span>{videoReady ? video.captions ? '소리와 자막은 재생 메뉴에서 조절할 수 있어요.' : '소리는 재생 메뉴에서 조절할 수 있어요.' : '시급부터 계약서 교부까지, 네 가지 체크'}</span></div>
    </section>
    <section className="guide-text" aria-labelledby="guide-steps-title"><h2 id="guide-steps-title">서명 전에 확인할 네 가지</h2><ol>{checklist.map((item, index) => <li key={item.title}><strong>{index + 1}. {item.title}</strong><span>{item.text}</span></li>)}</ol><p className="education-source">근거 자료: <a href="https://www.moel.go.kr/mainpop2.do" target="_blank" rel="noreferrer">고용노동부 · 근로계약서 작성 안내 (새 탭)</a></p><p className="education-note">기본 확인사항을 소개하는 교육 콘텐츠예요. 개별 근로조건에 대한 정확한 판단은 공식 안내와 상담을 통해 확인해 주세요.</p></section>
    <div className="guide-actions"><ButtonLink variant="secondary" href="#/">서비스 소개로</ButtonLink><ButtonLink href="#/workspace">내 문서 확인하기</ButtonLink></div>
  </div>
}
