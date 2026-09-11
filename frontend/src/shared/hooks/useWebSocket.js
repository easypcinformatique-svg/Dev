import { useEffect, useRef, useCallback, useState } from 'react'

export function useWebSocket(onMessage) {
  const ws = useRef(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimeout = useRef(null)

  const connect = useCallback(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/kitchen`
    ws.current = new WebSocket(wsUrl)

    ws.current.onopen = () => {
      setConnected(true)
      // Ping pour garder la connexion ouverte
      const pingInterval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send('ping')
        }
      }, 30000)
      ws.current._pingInterval = pingInterval
    }

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.event !== 'pong') {
          onMessage(data)
        }
      } catch (e) {
        // ignore
      }
    }

    ws.current.onclose = () => {
      setConnected(false)
      if (ws.current?._pingInterval) clearInterval(ws.current._pingInterval)
      // Reconnexion auto
      reconnectTimeout.current = setTimeout(connect, 3000)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [onMessage])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      if (ws.current?._pingInterval) clearInterval(ws.current._pingInterval)
      ws.current?.close()
    }
  }, [connect])

  return { connected }
}
