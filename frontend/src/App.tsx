function App() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8 sm:px-10">
      <header className="flex items-center justify-between border-b border-white/10 pb-6">
        <a href="/" className="flex items-center gap-3 text-lg font-semibold tracking-tight text-white" aria-label="ZUNO home">
          <span className="grid size-9 place-items-center rounded-xl bg-violet-500 font-bold">Z</span>
          ZUNO
        </a>
        <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-400">Local workspace</span>
      </header>

      <section className="flex flex-1 flex-col items-center justify-center py-16 text-center">
        <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-violet-300">AI website builder</p>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-6xl">What would you like to build?</h1>
        <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">
          Describe a website in plain language. ZUNO will plan, build, and help you refine it.
        </p>
        <div className="mt-10 w-full max-w-2xl rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-left shadow-2xl shadow-black/20">
          <label htmlFor="website-prompt" className="sr-only">Describe your website</label>
          <textarea
            id="website-prompt"
            rows={4}
            placeholder="A portfolio for a photographer with a dark editorial style..."
            className="w-full resize-none bg-transparent p-3 text-sm leading-6 text-white outline-none placeholder:text-zinc-600"
          />
          <div className="flex items-center justify-between border-t border-white/10 px-2 pt-3">
            <span className="text-xs text-zinc-500">Generation workflow will be added in a later phase.</span>
            <button type="button" disabled className="rounded-lg bg-violet-500/50 px-4 py-2 text-sm font-medium text-white/70" title="Available in a later phase">
              Start building
            </button>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 pt-5 text-center text-xs text-zinc-600">ZUNO · Project setup</footer>
    </main>
  )
}

export default App
