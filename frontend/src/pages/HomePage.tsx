import { useState } from 'react'
import { useNavigate } from 'react-router'
import type { FragmentInput } from '../api'
import { CatalogList } from '../catalog/CatalogList'
import { CatalogToolbar } from '../catalog/CatalogToolbar'
import { FragmentForm } from '../forms/FragmentForm'
import { FragmentRow } from '../rows/FragmentRow'
import { SongRow } from '../rows/SongRow'
import { useAppState } from '../state/AppStateContext'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { FormDialog } from '../ui/FormDialog'
import { NewMenu } from '../ui/NewMenu'
import { PageHeading } from '../ui/PageHeading'
import { RandomFragmentInline } from './RandomFragmentInline'

/**
 * Search songs and fragments together, in the same layout as the Songs and Fragments pages. Which kinds
 * to show is chosen with SHOW. A small random fragment sits beside the title. The New menu adds a
 * fragment in a box over the page, or opens the song page to write a song.
 */
const EMPTY_FRAGMENT: FragmentInput = { text: '', tags: [] }

export function HomePage() {
  const { notebook, songs, fragments, homeTags } = useAppState()
  const { page, query } = notebook
  const navigate = useNavigate()
  const [addingFragment, setAddingFragment] = useState(false)

  /** Add a fragment, and go to the first page, newest first, where it appears. */
  async function addFragment(input: FragmentInput) {
    await fragments.create(input)
    notebook.showNewest()
  }

  // On phones the New button sits beside the search box; on wider screens it is in the top row.
  const newMenu = <NewMenu onNewFragment={() => setAddingFragment(true)} onNewSong={() => navigate('/songs/new')} />

  return (
    <div className="flex flex-col gap-4 sm:gap-9 lg:h-full lg:gap-5">
      <div className="hidden flex-wrap items-center justify-between gap-4 sm:flex">
        {/* The top nav already says Home, so phones skip the title. */}
        <div className="hidden sm:block">
          <PageHeading title="Home" />
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {/* Hidden on phones for now, to keep the search box near the top. */}
          <div className="hidden sm:block">
            <RandomFragmentInline />
          </div>

          {newMenu}
        </div>
      </div>

      <CatalogToolbar
        placeholder="Search songs and fragments"
        phoneAction={newMenu}
        searchText={notebook.searchText}
        onSearchText={notebook.setSearchText}
        allTags={homeTags}
        selectedTags={query.tags}
        onToggleTag={notebook.toggleTag}
        years={page?.years ?? []}
        year={query.year}
        onYear={notebook.setYear}
        sort={query.sort}
        onSort={notebook.setSort}
        scope={query.scope}
        onScope={notebook.setScope}
      />

      <CatalogList
        noun="result"
        emptyMessage="Nothing in your notebook yet. Add a song or a fragment to get started."
        page={page}
        sort={query.sort}
        hasFilters={notebook.hasFilters}
        loading={notebook.loading}
        loadError={notebook.loadError}
        actionError={songs.actionError || fragments.actionError}
        onPage={notebook.goToPage}
        onClearFilters={notebook.clearFilters}
        renderRow={(entry) => {
          if (entry.kind === 'song') {
            return (
              <SongRow
                song={entry}
                showKind={true}
                onEdit={() => navigate(`/songs/${entry.id}`)}
                onDelete={() => songs.setDeletingId(entry.id)}
              />
            )
          }

          return (
            <FragmentRow
              fragment={entry}
              showKind={true}
              editing={fragments.editingId === entry.id}
              onEdit={() => fragments.setEditingId(entry.id)}
              onCancelEdit={() => fragments.setEditingId(null)}
              onSave={(input) => fragments.update(entry.id, input)}
              onDelete={() => fragments.setDeletingId(entry.id)}
            />
          )
        }}
      />

      <FormDialog open={addingFragment} title="New fragment" onClose={() => setAddingFragment(false)}>
        <FragmentForm
          initial={EMPTY_FRAGMENT}
          submitLabel="Add fragment"
          clearOnSuccess={true}
          onSubmit={addFragment}
          onCancel={() => setAddingFragment(false)}
          cancelLabel="Done"
        />
      </FormDialog>

      <ConfirmDialog
        open={Boolean(songs.deletingId)}
        title="Delete this song?"
        description="It will be removed for good. This can't be undone."
        confirmLabel="Delete"
        pending={songs.deleting}
        onConfirm={songs.confirmDelete}
        onCancel={() => songs.setDeletingId(null)}
      />

      <ConfirmDialog
        open={Boolean(fragments.deletingId)}
        title="Delete this fragment?"
        description="It will be removed for good. This can't be undone."
        confirmLabel="Delete"
        pending={fragments.deleting}
        onConfirm={fragments.confirmDelete}
        onCancel={() => fragments.setDeletingId(null)}
      />
    </div>
  )
}
