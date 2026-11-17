import { Component, type ReactNode } from 'react'

export class PlotBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed ? <p role="alert" className="p-6 text-sm">No se pudo cargar la gráfica. La tabla sigue disponible; recargá la página para reintentar.</p> : this.props.children
  }
}
