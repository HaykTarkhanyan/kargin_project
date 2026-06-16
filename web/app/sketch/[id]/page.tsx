import { notFound } from "next/navigation";
import { ALL, byId } from "@/lib/data";
import WatchView from "@/components/WatchView";
import LogView from "@/components/LogView";

export function generateStaticParams() {
  return ALL.map((s) => ({ id: s.id }));
}

export default async function SketchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const s = byId(id);
  if (!s) notFound();
  return (
    <>
      <LogView sketchId={s.id} />
      <WatchView s={s} />
    </>
  );
}
