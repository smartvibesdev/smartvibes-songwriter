import { useState } from 'react'
import { getIdToken, signOut } from './auth'
import { Fragments } from './Fragments'
import { Search } from './Search'
import { Songs } from './Songs'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Tab = 'songs' | 'fragments' | 'search'

const TABS: { id: Tab; label: string }[] = [
  { id: 'songs', label: 'Songs' },
  { id: 'fragments', label: 'Fragments' },
  { id: 'search', label: 'Search' },
]

type HomeProps = {
  /** Called when the user signs out, or when their session turns out to have expired. */
  onSignedOut: () => void
}

/** What a signed-in user sees: tabs for songs, fragments and search. */
export function Home({ onSignedOut }: HomeProps) {
  const [tab, setTab] = useState<Tab>('songs')
  const [me, setMe] = useState('')

  function handleSignOut() {
    signOut()
    onSignedOut()
  }

  async function callMe() {
    const token = await getIdToken()

    if (token === null) {
      onSignedOut()

      return
    }

    const response = await fetch(`${API_URL}/me`, { headers: { Authorization: `Bearer ${token}` } })

    setMe(`${response.status} ${await response.text()}`)
  }

  return (
    <>
      <nav className="tabs">
        {TABS.map(({ id, label }) => (
          <button key={id} type="button" aria-pressed={tab === id} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}{' '}
        <button type="button" onClick={handleSignOut}>
          Sign out
        </button>
      </nav>

      {tab === 'songs' && <Songs />}
      {tab === 'fragments' && <Fragments />}
      {tab === 'search' && <Search />}

      <p>
        <button type="button" onClick={callMe}>
          Call /me
        </button>
      </p>

      {me && <pre>{me}</pre>}
    </>
  )
}
