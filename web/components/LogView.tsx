"use client";
import { useEffect } from "react";
import { logEvent } from "@/lib/log";

/** Logs a sketch "open" once when a watch page mounts. Renders nothing. */
export default function LogView({ sketchId }: { sketchId: string }) {
  useEffect(() => {
    logEvent("open", { sketchId, source: "watch" });
  }, [sketchId]);
  return null;
}
