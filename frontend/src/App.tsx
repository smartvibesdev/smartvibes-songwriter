import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function App() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(d.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <main>
      <h1>SmartVibes Songwriter</h1>
      <p>API status: {status}</p>
    </main>
  )
}

export default App
