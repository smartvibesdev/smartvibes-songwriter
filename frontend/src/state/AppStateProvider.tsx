import { type ReactNode, useCallback, useState } from 'react'
import {
  type Fragment,
  type FragmentInput,
  type Song,
  type SongInput,
  createFragment,
  createSong,
  deleteFragment,
  deleteSong,
  listNotebook,
  listTags,
  updateFragment,
  updateSong,
} from '../api'
import { useItemActions } from '../catalog/useItemActions'
import { FIRST_PAGE, useList } from '../catalog/useList'
import { useRandomFragment } from '../home/useRandomFragment'
import { useLoaded } from '../useLoaded'
import { AppStateContext } from './AppStateContext'

// These are declared out here so they stay the same objects on every render.
const SONG_API = { create: createSong, update: updateSong, remove: deleteSong }
const FRAGMENT_API = { create: createFragment, update: updateFragment, remove: deleteFragment }
const listAllTags = () => listTags('both')

// Home starts on everything (songs and fragments together); SHOW changes that.
const HOME_FIRST_PAGE = { ...FIRST_PAGE, scope: 'both' as const }

/**
 * Holds the state of the screens above the page, so nothing is lost when a part of the screen
 * comes and goes: Home's filters, page number and loaded list, its tag list, the random
 * fragment, and which item is being edited or deleted. Adding, editing or deleting a song or
 * fragment reloads Home's list and tags. Signing out removes this provider, so nothing carries
 * over to the next person.
 */
export function AppStateProvider({ children }: { children: ReactNode }) {
  // Goes up after every change to a song or fragment.
  const [dataVersion, setDataVersion] = useState(0)
  const onChange = useCallback(() => setDataVersion((current) => current + 1), [])

  const songs = useItemActions<Song, SongInput>(SONG_API, onChange)
  const fragments = useItemActions<Fragment, FragmentInput>(FRAGMENT_API, onChange)

  const notebook = useList(listNotebook, { first: HOME_FIRST_PAGE, refreshKey: dataVersion })
  const { data: homeTags } = useLoaded(listAllTags, dataVersion)
  const random = useRandomFragment()

  return (
    <AppStateContext.Provider value={{ songs, fragments, notebook, homeTags: homeTags ?? [], random }}>
      {children}
    </AppStateContext.Provider>
  )
}
