'use client'

import { useState, useRef, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface DeviceInfo {
  room: string
  type: string
  status: string
  properties: Record<string, any>
}

const EXAMPLES = [
  'Turn on the bedroom light',
  'Set living room AC to 25 degrees',
  'Dim the lights to 50%',
  'Play some music',
  'What devices are on?',
]

const ROOM_NAMES: Record<string, string> = {
  bedroom: 'Bedroom',
  living_room: 'Living Room',
  kitchen: 'Kitchen',
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [devices, setDevices] = useState<Record<string, DeviceInfo>>({})
  const messagesEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchDevices()
  }, [])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function fetchDevices() {
    try {
      const res = await fetch(`${API_URL}/devices`)
      if (res.ok) {
        setDevices(await res.json())
      }
    } catch (e) {
      console.error('Failed to fetch devices:', e)
    }
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok) throw new Error('Request failed')

      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      setDevices(data.devices)
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to get response' }])
    } finally {
      setLoading(false)
    }
  }

  function formatProps(props: Record<string, any>): string {
    return Object.entries(props)
      .filter(([_, v]) => v !== null)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')
  }

  return (
    <div className="container">
      <header className="header">
        <h1>🏠 Home Assistant</h1>
        <p>AI-powered smart home control</p>
      </header>

      <main className="main">
        <div className="chat-panel">
          <div className="messages">
            {messages.length === 0 && (
              <div style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
                Try saying: "Turn on the bedroom light"
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                {msg.content}
              </div>
            ))}
            {loading && <div className="message assistant">Thinking...</div>}
            <div ref={messagesEnd} />
          </div>

          <div className="input-area">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
              placeholder="Type a command..."
              disabled={loading}
            />
            <button onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>
        </div>

        <aside className="device-panel">
          <h3>Devices</h3>
          {Object.entries(devices).map(([id, dev]) => (
            <div key={id} className="device-card">
              <div className="name">{ROOM_NAMES[dev.room] || dev.room} {dev.type}</div>
              <div className={`status ${dev.status}`}>{dev.status.toUpperCase()}</div>
              <div className="props">{formatProps(dev.properties)}</div>
            </div>
          ))}

          <div className="examples">
            <h4>Quick Commands</h4>
            {EXAMPLES.map((ex, i) => (
              <button key={i} className="example-btn" onClick={() => sendMessage(ex)}>
                {ex}
              </button>
            ))}
          </div>
        </aside>
      </main>
    </div>
  )
}
