import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { EditorState } from '@codemirror/state'
import { drawSelection, EditorView, keymap, placeholder } from '@codemirror/view'
import { useEffect, useRef } from 'react'

type TextEditorProps = {
  /** The text when the editor first appears. Changing it later does not replace what is typed. */
  initialValue: string
  onChange: (value: string) => void
  /** What screen readers call the editor. */
  label: string
  placeholderText?: string
  /** Typing or pasting past this many characters is ignored. */
  maxLength: number
}

// Colours come from the app's theme variables, so the editor follows light and dark mode.
const THEME = EditorView.theme({
  '&': { height: '100%', color: 'var(--foreground)', backgroundColor: 'transparent', fontSize: '1.125rem' },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { overflow: 'auto', fontFamily: 'inherit', lineHeight: '1.7' },
  '.cm-content': { padding: '1rem 1.25rem', caretColor: 'var(--foreground)' },
  '.cm-line': { padding: '0' },
  '.cm-cursor': { borderLeftColor: 'var(--foreground)' },
  '.cm-selectionBackground': { backgroundColor: 'color-mix(in srgb, var(--primary) 30%, transparent) !important' },
  '.cm-placeholder': { color: 'var(--muted)' },
})

/**
 * A plain-text editor (CodeMirror 6) for lyrics: line wrapping, undo and redo, no formatting.
 * It owns the text while it is on screen and reports every change through `onChange`.
 */
export function TextEditor({ initialValue, onChange, label, placeholderText = '', maxLength }: TextEditorProps) {
  const host = useRef<HTMLDivElement>(null)
  const startingText = useRef(initialValue)
  const reportChange = useRef(onChange)

  useEffect(() => {
    reportChange.current = onChange
  }, [onChange])

  useEffect(() => {
    if (host.current === null) {
      return
    }

    const view = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: startingText.current,
        extensions: [
          history(),
          drawSelection(),
          keymap.of([...defaultKeymap, ...historyKeymap]),
          EditorView.lineWrapping,
          placeholder(placeholderText),
          EditorView.contentAttributes.of({ 'aria-label': label, 'aria-multiline': 'true' }),
          EditorState.transactionFilter.of((transaction) => (transaction.newDoc.length > maxLength ? [] : transaction)),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              reportChange.current(update.state.doc.toString())
            }
          }),
          THEME,
        ],
      }),
    })

    return () => view.destroy()
  }, [label, maxLength, placeholderText])

  return <div ref={host} className="h-full min-h-0" />
}
