import { useState } from 'react'
import { Icon } from '../components/common/Icon'
import { ButtonLink } from '../components/common/ButtonLink'

type GuideVideo = { src: string; poster?: string; captions?: string }

export function GuidePage({ video }: { video?: GuideVideo }) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const videoReady = video?.src && failedSource !== video.src

  return <div className="guide-page">
    <div className="guide-heading"><p className="eyebrow">SAVER GUIDE</p><h1>Saver, 이렇게 이용해요</h1><p>문서를 올리고, 내용을 확인하고, 근거를 살펴보세요.</p></div>
    <section className="guide-card" aria-label="서비스 이용 안내 영상">
      {videoReady ? <video key={video.src} src={video.src} className="guide-player" controls playsInline preload="metadata" poster={video.poster} onError={() => setFailedSource(video.src)}>
        {video.captions && <track kind="captions" src={video.captions} srcLang="ko" label="한국어" default />}영상 재생을 지원하지 않는 브라우저예요. 아래 글로 된 이용 안내를 확인해 주세요.
      </video> : <div className="guide-placeholder"><span className="guide-placeholder__icon"><Icon name="file" width="32" height="32" /></span><span className="guide-placeholder__label">SAVER · 이용 안내</span><h2>{video?.src ? '영상을 불러오지 못했어요' : '소개 영상을 준비 중이에요'}</h2><p>{video?.src ? '아래 글로 된 이용 안내를 확인해 주세요.' : '영상이 준비되기 전에도 아래 안내로 쉽게 시작할 수 있어요.'}</p><span className="guide-placeholder__tag">문서 이해의 시작, Saver</span></div>}
      <div className="guide-card__caption"><span>서비스 이용 안내</span><span>{videoReady ? video.captions ? '소리와 자막은 재생 메뉴에서 조절할 수 있어요.' : '소리는 재생 메뉴에서 조절할 수 있어요.' : '문서 사진만 준비해 주세요.'}</span></div>
    </section>
    <section className="guide-text" aria-labelledby="guide-steps-title"><h2 id="guide-steps-title">글로도 쉽게 살펴보세요</h2><ol><li><strong>문서를 올려요</strong><span>안내받을 언어를 고르고 근로계약서나 급여명세서 사진을 준비해요.</span></li><li><strong>내용을 확인해요</strong><span>읽어낸 시급·근무시간을 원본과 비교하고, 다른 부분은 직접 수정해요.</span></li><li><strong>근거와 함께 이해해요</strong><span>확인할 항목과 공식 Q&A를 살펴보고 궁금한 부분을 질문해요.</span></li></ol></section>
    <div className="guide-actions"><ButtonLink variant="secondary" href="#/">서비스 소개로</ButtonLink><ButtonLink href="#/workspace">서비스 이용하기</ButtonLink></div>
  </div>
}
