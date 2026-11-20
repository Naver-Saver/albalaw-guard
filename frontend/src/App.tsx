import { useEffect, useState } from 'react'
import { fetchHealth } from './api'

const FEATURES = [
  { title: '계약서·급여명세서 점검', desc: '사진을 올리면 시급·근무시간을 읽고 최저임금·주휴수당을 계산해요.' },
  { title: '대화 기록 정리', desc: '사장님과의 대화 녹음을 날짜별 핵심 발언 타임라인으로 정리해요.' },
  { title: '빠른 음성 질문', desc: '"주휴수당 받을 수 있어?" 말로 물어보면 공식 Q&A를 근거로 답해요.' },
  { title: '알바 시작 전 체크리스트', desc: '짧은 교육 영상으로 꼭 알아야 할 내용을 확인해요.' },
]

export default function App() {
  const [server, setServer] = useState('확인 중…')

  useEffect(() => {
    fetchHealth()
      .then((h) => setServer(`서버 정상 (v${h.version})`))
      .catch(() => setServer('서버에 연결할 수 없어요'))
  }, [])

  return (
    <main>
      <h1>알바생 노동권 지킴이</h1>
      <p className="status">{server}</p>
      {FEATURES.map((f) => (
        <section className="card" key={f.title}>
          <h2>{f.title}</h2>
          <p>{f.desc}</p>
        </section>
      ))}
      <p className="notice">
        이 서비스는 법률 자문이 아니며, 정부 공식 Q&A를 근거로 확인이 필요한 부분을 안내합니다.
        정확한 판단은 고용노동부(국번 없이 1350) 또는 대한법률구조공단(132)에 문의하세요.
      </p>
    </main>
  )
}
