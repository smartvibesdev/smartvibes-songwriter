import { createContext, useContext } from 'react'
import type { Fragment, FragmentInput, NotebookEntry, Song, SongInput, TagCount } from '../api'
import type { ItemActions } from '../catalog/useItemActions'
import type { useList } from '../catalog/useList'
import type { useRandomFragment } from '../home/useRandomFragment'

/** Everything the screens share, so it survives switching pages. */
export type AppState = {
  /** Adding, editing and deleting songs. */
  songs: ItemActions<Song, SongInput>
  /** Adding, editing and deleting fragments. */
  fragments: ItemActions<Fragment, FragmentInput>
  /** Home's mixed list of songs and fragments. */
  notebook: ReturnType<typeof useList<NotebookEntry>>
  /** Every tag across songs and fragments, for Home's tag filter. */
  homeTags: TagCount[]
  random: ReturnType<typeof useRandomFragment>
}

export const AppStateContext = createContext<AppState | null>(null)

/** The shared app state. Only works inside `AppStateProvider`. */
export function useAppState(): AppState {
  const state = useContext(AppStateContext)

  if (state === null) {
    throw new Error('useAppState must be used inside AppStateProvider')
  }

  return state
}
