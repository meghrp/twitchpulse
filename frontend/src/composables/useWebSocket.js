import { ref } from 'vue'

const RECONNECT_DELAY = 2000

export function useWebSocket() {
  const status = ref('idle')
  let socket
  let lastUrl = ''
  let reconnectHandle
  let messageHandler = () => {}

  const connect = (url, handler) => {
    lastUrl = url
    messageHandler = handler
    disposeSocket()
    status.value = 'connecting'

    try {
      socket = new WebSocket(url)
    } catch (error) {
      status.value = 'error'
      scheduleReconnect()
      return
    }

    socket.onopen = () => {
      status.value = 'open'
    }

    socket.onmessage = (event) => {
      if (typeof handler === 'function') {
        try {
          const data = JSON.parse(event.data)
          handler(data)
        } catch {
          // ignore malformed packets
        }
      }
    }

    socket.onclose = () => {
      status.value = 'closed'
      scheduleReconnect()
    }

    socket.onerror = () => {
      status.value = 'error'
      disposeSocket()
      scheduleReconnect()
    }
  }

  const scheduleReconnect = () => {
    if (!lastUrl) return
    clearTimeout(reconnectHandle)
    reconnectHandle = setTimeout(() => {
      connect(lastUrl, messageHandler)
    }, RECONNECT_DELAY)
  }

  const disconnect = () => {
    clearTimeout(reconnectHandle)
    if (socket && socket.readyState <= 1) {
      socket.close()
    }
    disposeSocket()
    status.value = 'closed'
  }

  const disposeSocket = () => {
    if (socket) {
      socket.onopen = null
      socket.onclose = null
      socket.onerror = null
      socket.onmessage = null
    }
  }

  return {
    status,
    connect,
    disconnect,
  }
}

