import { useCallback, useEffect, useState } from 'react'

// El componente que lo usa se desmonta al editar/recalcular: no conserva timers.
export function usePlayback(count: number) {
  const [selected, setSelected] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [delay, setDelay] = useState(1000)
  const select = useCallback((index: number) => {
    setPlaying(false)
    setSelected(Math.max(0, Math.min(Math.max(0, count - 1), index)))
  }, [count])

  useEffect(() => {
    if (!playing) return
    if (selected >= count - 1) { setPlaying(false); return }
    const timer = window.setTimeout(() => setSelected(index => index + 1), delay)
    return () => window.clearTimeout(timer)
  }, [playing, selected, count, delay])

  const toggle = () => {
    if (count < 2) return
    if (!playing && selected === count - 1) setSelected(0)
    setPlaying(value => !value)
  }
  return { selected, playing, delay, setDelay, select, toggle }
}
