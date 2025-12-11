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

interface ScheduleInfo {
  id: string
  type: string
  trigger_time: string
  repeat: string
  description: string
  message: string
  status: string
}

const EXAMPLES = [
  'Turn on the bedroom light',
  'Set living room AC to 25 degrees',
  'Remind me to drink water in 10 minutes',
  'Turn off lights at 11pm daily',
  'What\'s scheduled?',
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
  const [schedules, setSchedules] = useState<ScheduleInfo[]>([])
  const messagesEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchDevices()
    fetchSchedules()
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

  async function fetchSchedules() {
    try {
      const res = await fetch(`${API_URL}/schedules`)
      if (res.ok) {
        setSchedules(await res.json())
      }
    } catch (e) {
      console.error('Failed to fetch schedules:', e)
    }
  }

  async function deleteSchedule(taskId: string) {
    try {
      const res = await fetch(`${API_URL}/schedules/${taskId}`, { method: 'DELETE' })
      if (res.ok) {
        fetchSchedules()
      }
    } catch (e) {
      console.error('Failed to delete schedule:', e)
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
      fetchSchedules()
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

  function formatTime(isoTime: string): string {
    const date = new Date(isoTime)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()
    const tomorrow = new Date(now)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const isTomorrow = date.toDateString() === tomorrow.toDateString()

    const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (isToday) return `Today ${timeStr}`
    if (isTomorrow) return `Tomorrow ${timeStr}`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + timeStr
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

        <aside className="side-panel">
          <div className="panel-section">
            <h3>Devices</h3>
            {Object.entries(devices).map(([id, dev]) => (
              <div key={id} className="device-card">
                <div className="name">{ROOM_NAMES[dev.room] || dev.room} {dev.type}</div>
                <div className={`status ${dev.status}`}>{dev.status.toUpperCase()}</div>
                <div className="props">{formatProps(dev.properties)}</div>
              </div>
            ))}
          </div>

          <div className="panel-section">
            <h3>Scheduled Tasks</h3>
            {schedules.length === 0 ? (
              <div className="empty-state">No scheduled tasks</div>
            ) : (
              schedules.filter(s => s.status === 'pending').map(schedule => (
                <div key={schedule.id} className="schedule-card">
                  <div className="schedule-header">
                    <span className={`schedule-type ${schedule.type}`}>
                      {schedule.type === 'reminder' ? '🔔' : '⚡'}
                    </span>
                    <span className="schedule-time">{formatTime(schedule.trigger_time)}</span>
                    {schedule.repeat !== 'once' && (
                      <span className="schedule-repeat">{schedule.repeat}</span>
                    )}
                  </div>
                  <div className="schedule-desc">
                    {schedule.type === 'reminder' ? schedule.message : schedule.description}
                  </div>
                  <button
                    className="schedule-delete"
                    onClick={() => deleteSchedule(schedule.id)}
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>

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
