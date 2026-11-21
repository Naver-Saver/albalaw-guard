export function validateRecording(file: Pick<File, 'name' | 'size'>): string | null {
  if (!/\.(m4a|mp3|wav)$/i.test(file.name)) return 'm4a, mp3, wav 파일을 선택해 주세요.'
  if (file.size === 0) return '빈 파일은 선택할 수 없어요.'
  if (file.size > 200 * 1024 * 1024) return '파일은 200MB 이하여야 해요.'
  return null
}
