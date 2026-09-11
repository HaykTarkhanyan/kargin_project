import type { Metadata } from "next";
import Link from "next/link";
import DataTable from "@/components/DataTable";
import { ALL } from "@/lib/data";

export const metadata: Metadata = {
  title: "Տվյալները — Կարգին Արխիվ",
  description: "Արխիվի ամբողջ աղյուսակը՝ զտիչներով, դասավորությամբ և ներբեռնումով։",
};

export default function DataPage() {
  const withText = ALL.filter((s) => s.text).length;
  const withTranscript = ALL.filter((s) => s.transcript).length;
  const withSongs = ALL.filter((s) => s.songs?.length).length;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12">
      <h1 className="font-display text-4xl sm:text-5xl">Տվյալները</h1>
      <p className="mt-4 max-w-[70ch] leading-relaxed opacity-80">
        Ամբողջ արխիվը մեկ աղյուսակում՝ {ALL.length} սքեթչ։ Զտիր, դասավորիր սյունակի վրա սեղմելով,
        և ներբեռնիր այն, ինչ մնաց՝ CSV կամ JSON։ Ներբեռնվածը պարունակում է նաև ամբողջական
        տեքստերը, վերծանումները և տեսարանի նկարագրությունները, որոնք աղյուսակում չեն երևում։
      </p>
      <p className="mt-3 max-w-[70ch] text-sm text-muted">
        {withText} սքեթչ ունի ձեռքով համադրված տեքստ · {withTranscript}՝ ավտոմատ վերծանում ·{" "}
        {withSongs}՝ ճանաչված երաժշտություն։ Այս էջի որոնումը պարզ զտիչ է (ուղիղ համընկնում).
        խելացի որոնման համար՝ <Link href="/" className="font-bold underline underline-offset-2">գլխավոր էջը</Link>։
      </p>
      <div className="mt-8">
        <DataTable />
      </div>
    </main>
  );
}
