import { listTags } from '../api'
import { PageHeading } from '../ui/PageHeading'
import { useLoaded } from '../useLoaded'
import { RandomFragmentCard } from './RandomFragmentCard'
import { SearchPanel } from './SearchPanel'

/** Search your notebook, or pull a random fragment for inspiration. */
export function ExplorePage() {
  const { data: tags } = useLoaded(listTags)

  return (
    <div className="flex flex-col gap-14">
      <PageHeading title="Explore" subtitle="Search your notebook, or let it surprise you." />

      <RandomFragmentCard />

      <SearchPanel tags={tags ?? []} />
    </div>
  )
}
