"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ALL } from "@/lib/data";

export default function RandomPage() {
  const router = useRouter();
  useEffect(() => {
    const s = ALL[Math.floor(Math.random() * ALL.length)];
    router.replace(`/sketch/${s.id}`);
  }, [router]);
  return <p className="p-10 text-center text-muted">Բացում ենք պատահական սքեթչ…</p>;
}
