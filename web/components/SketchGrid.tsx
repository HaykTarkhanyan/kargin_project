import type { Sketch } from "@/lib/types";
import SketchCard from "./SketchCard";

export default function SketchGrid({ items }: { items: Sketch[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      {items.map((s) => <SketchCard key={s.id} sketch={s} />)}
    </div>
  );
}
