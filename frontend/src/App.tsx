import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import './App.css'

type Message = {
  role: 'user' | 'assistant'
  text: string
}

type GeneratedFile = {
  path: string
  size: number
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

function App() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [files, setFiles] = useState<GeneratedFile[]>([])
  const [previewUrl, setPreviewUrl] = useState('')
  const [isBuilding, setIsBuilding] = useState(false)
  const [error, setError] = useState('')
  const conversationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/files`)
      .then(async (response) => {
        if (!response.ok) return []
        return (await response.json()) as GeneratedFile[]
      })
      .then((generatedFiles) => {
        setFiles(generatedFiles)
        if (generatedFiles.some((file) => file.path === 'index.html')) {
          setPreviewUrl(`${API_BASE_URL}/preview?refresh=${Date.now()}`)
        }
      })
      .catch(() => {
        // The chat request will show a clear error if the backend is unavailable.
      })
  }, [])

  useEffect(() => {
    conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isBuilding])

  async function submitPrompt(event?: FormEvent) {
    event?.preventDefault()
    const nextPrompt = prompt.trim()
    if (!nextPrompt || isBuilding) return

    setMessages((current) => [...current, { role: 'user', text: nextPrompt }])
    setPrompt('')
    setError('')
    setIsBuilding(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: nextPrompt }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'The build request failed.')
      }

      const generatedFiles = (data.files || []) as GeneratedFile[]
      setFiles(generatedFiles)
      setMessages((current) => [...current, { role: 'assistant', text: data.message || 'Your website is ready.' }])
      if (generatedFiles.some((file) => file.path === 'index.html')) {
        setPreviewUrl(`${API_BASE_URL}/preview?refresh=${Date.now()}`)
      }
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not reach the backend.'
      setError(message)
      setMessages((current) => [...current, { role: 'assistant', text: 'I could not finish that build. Check the error below and try again.' }])
    } finally {
      setIsBuilding(false)
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submitPrompt()
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ZUNO home">zuno<span>.</span></a>
        <div className="project-name"><span className="project-indicator" />Untitled website</div>
        <span className="topbar-label">Web studio</span>
      </header>

      <section className="workspace" aria-label="Website builder">
        <aside className="chat-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Project</p>
              <h1>Conversation</h1>
            </div>
            <span className="file-count"><span className="file-count-dot" />{files.length} {files.length === 1 ? 'file' : 'files'}</span>
          </div>

          <div className="conversation" ref={conversationRef} aria-live="polite">
            {messages.length === 0 ? (
              <div className="welcome-card">
                <h2>Start with an idea.</h2>
                <p>Describe a page you need. You can refine it with another message after it’s built.</p>
                <button className="suggestion" onClick={() => setPrompt('Create a clean portfolio website for a photographer')}>
                  Try a photographer portfolio <span>↗</span>
                </button>
              </div>
            ) : (
              messages.map((message, index) => (
                <article className={`message message-${message.role}`} key={`${message.role}-${index}`}>
                  <span className="message-author">{message.role === 'user' ? 'You' : 'Zuno'}</span>
                  <p>{message.text}</p>
                </article>
              ))
            )}
            {isBuilding && (
              <div className="message message-assistant building-message">
                <span className="message-author">Zuno</span>
                <p><span className="loader" /> Working on it…</p>
              </div>
            )}
          </div>

          <form className="composer" onSubmit={submitPrompt}>
            <label className="sr-only" htmlFor="prompt">Describe a website or change</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Describe a website or ask for a change…"
              rows={3}
              disabled={isBuilding}
            />
            {error && <p className="error-message">{error}</p>}
            <div className="composer-footer">
              <span>Enter to send <i /> Shift + Enter for a new line</span>
              <button className="send-button" type="submit" disabled={!prompt.trim() || isBuilding}>
                {isBuilding ? 'Building…' : 'Build'} <span aria-hidden="true">↑</span>
              </button>
            </div>
          </form>
        </aside>

        <section className="preview-panel" aria-label="Website preview">
          <div className="preview-toolbar">
            <div className="preview-heading">Preview</div>
            <div className="preview-address">/ generated site</div>
            {previewUrl ? (
              <button className="refresh-button" aria-label="Refresh preview" onClick={() => setPreviewUrl(`${API_BASE_URL}/preview?refresh=${Date.now()}`)}>↻</button>
            ) : <span className="toolbar-spacer" />}
          </div>
          {previewUrl ? (
            <iframe key={previewUrl} className="preview-frame" src={previewUrl} title="Generated website preview" />
          ) : (
            <div className="preview-empty">
              <h2>No preview yet</h2>
              <p>Send a prompt and the generated website will appear here.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  )
}

export default App
