import { notFound } from "next/navigation";
import { ALL, byId } from "@/lib/data";
import WatchView from "@/components/WatchView";

export function generateStaticParams() {
  return ALL.map((s) => ({ id: s.id }));
}

export default async function SketchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const s = byId(id);
  if (!s) notFound();
  return <WatchView s={s} />;
}
