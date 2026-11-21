export const MAX_VOICE_SECONDS = 60
export function encodeWav(samples: Float32Array, rate: number): Blob {
  if (!Number.isInteger(rate) || rate < 8000 || rate > 96000 || samples.length > rate * MAX_VOICE_SECONDS || !samples.length) throw new Error('60초 이하의 음성을 준비해 주세요.')
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)) }
  text(0, 'RIFF'); view.setUint32(4, buffer.byteLength - 8, true); text(8, 'WAVE'); text(12, 'fmt ')
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  text(36, 'data'); view.setUint32(40, samples.length * 2, true)
  samples.forEach((value, index) => { const clamped = Math.max(-1, Math.min(1, value)); view.setInt16(44 + index * 2, clamped < 0 ? clamped * 32768 : clamped * 32767, true) })
  return new Blob([buffer], { type: 'audio/wav' })
}

export async function prepareVoiceFile(file: File): Promise<File> {
  if (!/\.(wav|mp3)$/i.test(file.name) || !file.size || file.size > 10 * 1024 * 1024) throw new Error('10MB 이하의 WAV 또는 MP3 파일을 선택해 주세요.')
  const context = new AudioContext({ sampleRate: 16000 })
  try {
    const decoded = await context.decodeAudioData(await file.arrayBuffer())
    if (decoded.duration > MAX_VOICE_SECONDS) throw new Error('질문 음성은 60초 이하여야 해요.')
    const samples = new Float32Array(decoded.length)
    for (let c = 0; c < decoded.numberOfChannels; c++) { const channel = decoded.getChannelData(c); for (let i = 0; i < samples.length; i++) samples[i] += channel[i] / decoded.numberOfChannels }
    return new File([encodeWav(samples, decoded.sampleRate)], 'voice-question.wav', { type: 'audio/wav' })
  } finally { await context.close() }
}

export async function startMicrophone(onFinished: (file: File | null) => void) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  let context: AudioContext | undefined
  try {
    // 16kHz를 먼저 쓰고, 마이크와 샘플레이트가 다른 컨텍스트 연결을 막는 브라우저(Firefox)에서는 기본값으로 다시 연다.
    let input: MediaStreamAudioSourceNode
    try {
      context = new AudioContext({ sampleRate: 16000 })
      input = context.createMediaStreamSource(stream)
    } catch {
      if (context && context.state !== 'closed') await context.close()
      context = new AudioContext()
      input = context.createMediaStreamSource(stream)
    }
    await context.resume()
    const processor = context.createScriptProcessor(4096, 1, 1)
    let chunks: Float32Array[] = []; let length = 0; let closed = false
    const rate = context.sampleRate
    let timer: ReturnType<typeof setTimeout>
    const stop = (discard = false) => {
      if (closed) return
      closed = true; clearTimeout(timer); processor.onaudioprocess = null
      processor.disconnect(); input.disconnect(); stream.getTracks().forEach(track => track.stop()); void context!.close()
      if (discard || !length) { chunks = []; onFinished(null); return }
      const samples = new Float32Array(length); let offset = 0
      for (const chunk of chunks) { samples.set(chunk, offset); offset += chunk.length }
      chunks = []; onFinished(new File([encodeWav(samples, rate)], 'voice-question.wav', { type: 'audio/wav' }))
    }
    processor.onaudioprocess = event => {
      const data = event.inputBuffer.getChannelData(0)
      const take = Math.min(data.length, rate * MAX_VOICE_SECONDS - length)
      if (take > 0) { chunks.push(data.slice(0, take)); length += take }
      if (length >= rate * MAX_VOICE_SECONDS) stop()
    }
    input.connect(processor); processor.connect(context.destination)
    timer = setTimeout(() => stop(), MAX_VOICE_SECONDS * 1000)
    return { stop, cancel: () => stop(true) }
  } catch (error) { stream.getTracks().forEach(track => track.stop()); if (context && context.state !== 'closed') await context.close(); throw error }
}
