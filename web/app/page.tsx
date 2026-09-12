import SearchExperience from "@/components/SearchExperience";
import CollectionStrip from "@/components/CollectionStrip";

// The strip is rendered here, on the server, and handed to the client component
// as a prop. That keeps collections.json out of the browser bundle.
export default function Home() { return <SearchExperience strip={<CollectionStrip />} />; }
