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

type Conversation = {
  id: string
  title: string
  created_at: string
}

type OpenFile = {
  path: string
  content: string
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

function App() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [files, setFiles] = useState<GeneratedFile[]>([])
  const [previewUrl, setPreviewUrl] = useState('')
  const [isBuilding, setIsBuilding] = useState(false)
  const [error, setError] = useState('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('Untitled website')
  const [previewMode, setPreviewMode] = useState<'desktop' | 'mobile'>('desktop')
  const [selectedFile, setSelectedFile] = useState<OpenFile | null>(null)
  const conversationRef = useRef<HTMLDivElement>(null)

  async function refreshConversations() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/conversations`)
      if (!response.ok) return
      setConversations((await response.json()) as Conversation[])
    } catch {
      // The list simply stays empty if the backend is unavailable.
    }
  }

  useEffect(() => {
    void refreshConversations()
  }, [])

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/files`)
      .then(async (response) => {
        if (!response.ok) return []
        return (await response.json()) as GeneratedFile[]
      })
      .then((generatedFiles) => {
        setFiles(generatedFiles)
        if (generatedFiles.some((file) => file.path === 'index.html')) {
          setPreviewUrl(`${API_BASE_URL}/preview/?refresh=${Date.now()}`)
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
        body: JSON.stringify({ prompt: nextPrompt, conversation_id: conversationId }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'The build request failed.')
      }

      const newConversationId = (data.conversation_id as string | undefined) || conversationId
      if (newConversationId) setConversationId(newConversationId)
      if (data.project) setProjectName(data.project as string)
      const generatedFiles = (data.files || []) as GeneratedFile[]
      setFiles(generatedFiles)
      setMessages((current) => [...current, { role: 'assistant', text: data.message || 'Your website is ready.' }])
      if (generatedFiles.some((file) => file.path === 'index.html')) {
        setPreviewUrl(newConversationId ? `${API_BASE_URL}/preview/${newConversationId}/?refresh=${Date.now()}` : `${API_BASE_URL}/preview/?refresh=${Date.now()}`)
      }
      void refreshConversations()
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not reach the backend.'
      setError(message)
      setMessages((current) => [...current, { role: 'assistant', text: 'I could not finish that build. Check the error below and try again.' }])
    } finally {
      setIsBuilding(false)
    }
  }

  async function loadConversation(id: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Could not open that conversation.')
      }
      setConversationId(data.id as string)
      setProjectName((data.title as string) || 'Untitled website')
      setMessages(((data.messages || []) as { role: 'user' | 'assistant'; content: string }[]).map((message) => ({ role: message.role, text: message.content })))
      const generatedFiles = (data.files || []) as GeneratedFile[]
      setFiles(generatedFiles)
      setPreviewUrl(generatedFiles.some((file) => file.path === 'index.html') ? `${API_BASE_URL}/preview/${data.id}/?refresh=${Date.now()}` : '')
      setError('')
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not open that conversation.'
      setError(message)
    }
  }

  function newConversation() {
    setConversationId(null)
    setProjectName('Untitled website')
    setMessages([])
    setFiles([])
    setPreviewUrl('')
    setError('')
    setPrompt('')
  }

  async function openFile(path: string) {
    try {
      const encoded = path.split('/').map(encodeURIComponent).join('/')
      const url = conversationId
        ? `${API_BASE_URL}/api/files/${encoded}?conversation_id=${conversationId}`
        : `${API_BASE_URL}/api/files/${encoded}`
      const response = await fetch(url)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Could not open that file.')
      }
      setSelectedFile({ path, content: data.content as string })
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not open that file.'
      setError(message)
    }
  }

  function refreshPreview() {
    setPreviewUrl(conversationId ? `${API_BASE_URL}/preview/${conversationId}/?refresh=${Date.now()}` : `${API_BASE_URL}/preview/?refresh=${Date.now()}`)
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submitPrompt()
    }
  }

  const suggestions = [
    { title: 'Photographer portfolio', prompt: 'Create a clean portfolio website for a photographer' },
    { title: 'Coffee shop landing page', prompt: 'Build a landing page for a small coffee shop with a menu section' },
    { title: 'AI engineer portfolio', prompt: 'Create a portfolio website for an AI engineer named Shahjan' },
  ]

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="ZUNO home">zuno<span>.</span></a>
        <button className="new-build" type="button" onClick={newConversation}>+ New build</button>

        <div className="sidebar-section">
          <p className="sidebar-label">Past builds</p>
          {conversations.length === 0 ? (
            <p className="sidebar-empty">No builds yet.</p>
          ) : (
            conversations.map((conversation) => (
              <button
                key={conversation.id}
                className={`sidebar-item${conversation.id === conversationId ? ' sidebar-item-active' : ''}`}
                type="button"
                onClick={() => void loadConversation(conversation.id)}
              >
                <span className="sidebar-item-title">{conversation.title}</span>
                <span className="sidebar-item-date">{formatDate(conversation.created_at)}</span>
              </button>
            ))
          )}
        </div>

        <div className="sidebar-section sidebar-files">
          <p className="sidebar-label">Files · {files.length}</p>
          {files.length === 0 ? (
            <p className="sidebar-empty">No files yet.</p>
          ) : (
            files.map((file) => (
              <button key={file.path} className="sidebar-item file-item" type="button" onClick={() => void openFile(file.path)}>
                <span className="sidebar-item-title">{file.path}</span>
                <span className="sidebar-item-date">{formatSize(file.size)}</span>
              </button>
            ))
          )}
        </div>

        <p className="sidebar-footer">zuno — AI website builder</p>
      </aside>

      <section className="main">
        <header className="topbar">
          <div className="project">
            <span className="project-dot" />
            <div>
              <h1>{projectName}</h1>
              <p>{conversationId ? 'Saved · click a past build to reopen it' : 'Describe a website and watch it build'}</p>
            </div>
          </div>
          <span className="topbar-label">Web studio</span>
        </header>

        <div className="workspace">
          <section className="chat-panel" aria-label="Conversation">
            <div className="conversation" ref={conversationRef} aria-live="polite">
              {messages.length === 0 ? (
                <div className="welcome">
                  <h2>What should we build?</h2>
                  <p>Describe a page you need. You can refine it with another message after it’s built.</p>
                  <div className="suggestions">
                    {suggestions.map((suggestion) => (
                      <button key={suggestion.title} className="suggestion-card" type="button" onClick={() => setPrompt(suggestion.prompt)}>
                        <span className="suggestion-title">{suggestion.title}</span>
                        <span className="suggestion-arrow">↗</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((message, index) => (
                  <article className={`message message-${message.role}`} key={`${message.role}-${index}`}>
                    <span className={`avatar avatar-${message.role}`}>{message.role === 'user' ? 'S' : 'Z'}</span>
                    <div className="message-body">
                      <span className="message-author">{message.role === 'user' ? 'You' : 'Zuno'}</span>
                      <p>{message.text}</p>
                    </div>
                  </article>
                ))
              )}
              {isBuilding && (
                <div className="message message-assistant building-message">
                  <span className="avatar avatar-assistant">Z</span>
                  <div className="message-body">
                    <span className="message-author">Zuno</span>
                    <p>Building your site<span className="dots"><i>.</i><i>.</i><i>.</i></span></p>
                  </div>
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
                <span>Enter to send · Shift + Enter for a new line</span>
                <button className="send-button" type="submit" disabled={!prompt.trim() || isBuilding} aria-label="Send">↑</button>
              </div>
            </form>
          </section>

          <section className="preview-panel" aria-label="Website preview">
            <div className="preview-toolbar">
              <div className="browser-dots" aria-hidden="true"><i /><i /><i /></div>
              <div className="preview-address">{previewUrl ? 'zuno.preview' : 'No preview yet'}</div>
              <div className="preview-actions">
                <div className="preview-toggle" role="group" aria-label="Preview size">
                  <button type="button" className={previewMode === 'desktop' ? 'active' : ''} onClick={() => setPreviewMode('desktop')}>Desktop</button>
                  <button type="button" className={previewMode === 'mobile' ? 'active' : ''} onClick={() => setPreviewMode('mobile')}>Mobile</button>
                </div>
                <button className="icon-button" type="button" aria-label="Refresh preview" onClick={refreshPreview}>↻</button>
                {previewUrl && (
                  <a className="icon-button open-link" href={previewUrl} target="_blank" rel="noreferrer" aria-label="Open preview in a new tab">↗</a>
                )}
              </div>
            </div>
            <div className={`preview-frame-wrap preview-${previewMode}`}>
              {previewUrl ? (
                <iframe key={previewUrl} className="preview-frame" src={previewUrl} title="Generated website preview" />
              ) : (
                <div className="preview-empty">
                  <h2>No preview yet</h2>
                  <p>Send a prompt and the generated website will appear here.</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </section>

      {selectedFile && (
        <div className="file-viewer-backdrop" onClick={() => setSelectedFile(null)}>
          <div className="file-viewer" role="dialog" aria-label={selectedFile.path} onClick={(event) => event.stopPropagation()}>
            <div className="file-viewer-header">
              <span>{selectedFile.path}</span>
              <button type="button" aria-label="Close file" onClick={() => setSelectedFile(null)}>✕</button>
            </div>
            <pre>{selectedFile.content}</pre>
          </div>
        </div>
      )}
    </main>
  )
}

export default App
