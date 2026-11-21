import { useEffect, useRef, useState } from 'react'
import { Button } from './common/Button'
import type { Language } from '../features/document-upload/validation'
import { synthesizeSpeech, translateText } from '../features/speech/client'

const LABEL: Record<Language, string> = { ko: '한국어', en: 'English', vi: 'Tiếng Việt', 'zh-CN': '中文' }

/** 질문 답변 본문: 선택 언어 번역(원문 함께 보기)과 답변 듣기(TTS). */
export function AnswerBody({ answer, language = 'ko' }: { answer: string; language?: Language }) {
  const [translated, setTranslated] = useState<string | null>(null)
  const [translateError, setTranslateError] = useState('')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [speaking, setSpeaking] = useState(false)
  const [speechError, setSpeechError] = useState('')
  const audioRef = useRef<HTMLAudioElement>(null)
  useEffect(() => {
    if (language === 'ko') return
    const controller = new AbortController()
    translateText(answer, language, controller.signal).then(text => { if (!controller.signal.aborted) setTranslated(text) }).catch(reason => { if (!controller.signal.aborted) setTranslateError(reason instanceof Error ? reason.message : '번역하지 못했어요.') })
    return () => controller.abort()
  }, [answer, language])
  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl) }, [audioUrl])

  const shown = translated ?? answer
  const speechLang: Language = translated ? language : 'ko'
  async function listen() {
    if (audioUrl) { void audioRef.current?.play(); return }
    setSpeaking(true); setSpeechError('')
    try { setAudioUrl(URL.createObjectURL(await synthesizeSpeech(shown, speechLang))) }
    catch (reason) { setSpeechError(reason instanceof Error ? reason.message : '음성을 만들지 못했어요.') }
    finally { setSpeaking(false) }
  }
  return <div className="answer-body">
    <p>{shown}</p>
    {language !== 'ko' && (translated ? <details><summary>한국어 원문 보기</summary><p>{answer}</p></details> : <p className="answer-body__note" role="status">{translateError ? `번역을 불러오지 못해 한국어로 보여드려요. ${translateError}` : `${LABEL[language]}로 번역하고 있어요.`}</p>)}
    <div className="answer-body__audio"><Button variant="secondary" loading={speaking} onClick={() => void listen()}>{audioUrl ? '다시 듣기' : '답변 듣기'}</Button>{audioUrl && <audio ref={audioRef} src={audioUrl} controls autoPlay aria-label="답변 음성" />}</div>
    {speechError && <p role="alert" className="answer-body__note">{speechError}</p>}
  </div>
}
