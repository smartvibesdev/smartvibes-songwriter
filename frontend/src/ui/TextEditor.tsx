import { defaultKeymap, history, historyKeymap, isolateHistory, undo } from '@codemirror/commands'
import { type ChangeSpec, EditorState, StateEffect, StateField, type Text } from '@codemirror/state'
import { Decoration, type DecorationSet, drawSelection, EditorView, keymap, placeholder } from '@codemirror/view'
import { type Ref, useEffect, useImperativeHandle, useRef } from 'react'
import type { ChatEdit } from '../api'

/** What a parent can ask the editor to do. */
export type TextEditorHandle = {
  /** Add text at the end (after a blank line if there is already text) and move the cursor after it. */
  append: (text: string) => void
  /** The text the user has selected, or the empty string. */
  selectedText: () => string
  /** All of the text. */
  getText: () => string
  /** The selected text and the lines (starting at 1) it covers, or null when nothing is selected. */
  selection: () => { text: string; startLine: number; endLine: number } | null
  /**
   * Make the changes in one step (so one Undo takes them all back) and highlight the new lines for a
   * few seconds. Returns a short description such as "Changed lines 4–7", or null if they did not fit.
   */
  applyEdits: (edits: ChatEdit[]) => string | null
  /** Take back the last change (the same as Cmd/Ctrl+Z). */
  undo: () => void
}

/** How long lines changed by the assistant stay highlighted. */
const HIGHLIGHT_MILLISECONDS = 5000

const setHighlight = StateEffect.define<{ from: number; to: number }[] | null>()

/** A background on each line that the assistant just changed. */
const highlightField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(highlights, transaction) {
    let next = highlights.map(transaction.changes)

    for (const effect of transaction.effects) {
      if (effect.is(setHighlight)) {
        next = effect.value === null ? Decoration.none : lineHighlights(transaction.state.doc, effect.value)
      }
    }

    return next
  },
  provide: (field) => EditorView.decorations.from(field),
})

function lineHighlights(doc: Text, ranges: { from: number; to: number }[]): DecorationSet {
  const marks = []
  let lastLine = 0

  for (const range of ranges) {
    const firstLine = Math.max(doc.lineAt(range.from).number, lastLine + 1)
    const endLine = doc.lineAt(range.to).number

    for (let number = firstLine; number <= endLine; number += 1) {
      marks.push(Decoration.line({ class: 'cm-ai-changed' }).range(doc.line(number).from))
      lastLine = number
    }
  }

  return Decoration.set(marks)
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high)
}

/** The change in the text for one edit, using positions in the text as it is now. */
function changeFor(doc: Text, edit: ChatEdit): ChangeSpec {
  const isEmpty = doc.length === 0

  if (edit.operation === 'append') {
    return { from: doc.length, insert: (isEmpty ? '' : '\n\n') + edit.text }
  }

  if (edit.operation === 'insert_after') {
    const line = clamp(edit.start_line ?? 0, 0, doc.lines)

    if (line === 0) {
      return { from: 0, insert: edit.text + (isEmpty ? '' : '\n') }
    }

    return { from: doc.line(line).to, insert: (isEmpty ? '' : '\n') + edit.text }
  }

  const start = clamp(edit.start_line ?? 1, 1, doc.lines)
  const end = clamp(edit.end_line ?? start, start, doc.lines)

  return { from: doc.line(start).from, to: doc.line(end).to, insert: edit.text }
}

function describeLines(first: number, last: number): string {
  return first === last ? `Changed line ${first}` : `Changed lines ${first}–${last}`
}

type TextEditorProps = {
  ref?: Ref<TextEditorHandle>
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
  '.cm-ai-changed': { backgroundColor: 'color-mix(in srgb, var(--accent) 22%, transparent)' },
})

/**
 * A plain-text editor (CodeMirror 6) for lyrics: line wrapping, undo and redo, no formatting.
 * It owns the text while it is on screen and reports every change through `onChange`.
 */
export function TextEditor({ ref, initialValue, onChange, label, placeholderText = '', maxLength }: TextEditorProps) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const startingText = useRef(initialValue)
  const reportChange = useRef(onChange)
  const highlightTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    reportChange.current = onChange
  }, [onChange])

  useImperativeHandle(ref, () => ({
    getText() {
      return view.current?.state.doc.toString() ?? ''
    },

    selection() {
      const editor = view.current

      if (editor === null) {
        return null
      }

      const { from, to } = editor.state.selection.main

      if (from === to) {
        return null
      }

      const doc = editor.state.doc

      return { text: doc.sliceString(from, to), startLine: doc.lineAt(from).number, endLine: doc.lineAt(to).number }
    },

    applyEdits(edits: ChatEdit[]) {
      const editor = view.current

      if (editor === null || edits.length === 0) {
        return null
      }

      // Every edit uses line numbers from the text as it was, so all are worked out from this one version.
      const doc = editor.state.doc
      const changed: { from: number; to: number }[] = []

      try {
        const transaction = editor.state.update({
          changes: edits.map((edit) => changeFor(doc, edit)),
          scrollIntoView: true,
          annotations: isolateHistory.of('full'),
        })

        transaction.changes.iterChangedRanges((_fromA, _toA, fromB, toB) => changed.push({ from: fromB, to: toB }))
        editor.dispatch(transaction)
      } catch {
        // Edits that overlap each other cannot be applied together.
        return null
      }

      // An added section starts with the line break after the line above it; that line did not change.
      const newDoc = editor.state.doc

      for (const range of changed) {
        while (range.from < range.to && newDoc.sliceString(range.from, range.from + 1) === '\n') {
          range.from += 1
        }
      }

      editor.dispatch({ effects: setHighlight.of(changed) })
      window.clearTimeout(highlightTimer.current)
      highlightTimer.current = window.setTimeout(() => {
        view.current?.dispatch({ effects: setHighlight.of(null) })
      }, HIGHLIGHT_MILLISECONDS)

      const first = newDoc.lineAt(Math.min(...changed.map((range) => range.from))).number
      const last = newDoc.lineAt(Math.max(...changed.map((range) => range.to))).number

      return describeLines(first, last)
    },

    undo() {
      if (view.current !== null) {
        undo(view.current)
      }
    },

    selectedText() {
      const editor = view.current

      if (editor === null) {
        return ''
      }

      const { from, to } = editor.state.selection.main

      return editor.state.sliceDoc(from, to)
    },

    append(text: string) {
      const editor = view.current

      if (editor === null) {
        return
      }

      const end = editor.state.doc.length
      const separator = end > 0 ? '\n\n' : ''

      editor.dispatch({
        changes: { from: end, insert: separator + text },
        selection: { anchor: end + separator.length + text.length },
        scrollIntoView: true,
      })
    },
  }))

  useEffect(() => {
    if (host.current === null) {
      return
    }

    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: startingText.current,
        extensions: [
          history(),
          highlightField,
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

    view.current = editor

    return () => {
      window.clearTimeout(highlightTimer.current)
      view.current = null
      editor.destroy()
    }
  }, [label, maxLength, placeholderText])

  return <div ref={host} className="h-full min-h-0" />
}
