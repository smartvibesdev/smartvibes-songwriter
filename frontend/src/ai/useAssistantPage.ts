import { useEffect, useRef } from 'react'
import { type PageTools, useAssistant } from './AssistantContext'

/** Lets the assistant read and change this page while it is on screen (the song page uses it). */
export function useAssistantPage(tools: PageTools) {
  const { registerPageTools } = useAssistant()
  const latest = useRef(tools)

  // The assistant always calls the newest functions, without registering again on every render.
  useEffect(() => {
    latest.current = tools
  })

  useEffect(() => {
    registerPageTools({
      getContext: () => latest.current.getContext(),
      setTitle: (text) => latest.current.setTitle(text),
      applyEdits: (edits) => latest.current.applyEdits(edits),
      undoEdits: () => latest.current.undoEdits(),
    })

    return () => registerPageTools(null)
  }, [registerPageTools])
}
