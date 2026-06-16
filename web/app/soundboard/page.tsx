import Soundboard from "@/components/Soundboard";

export const metadata = {
  title: "Ֆրազների պատ — Կարգին Արխիվ",
  description: "Կարգինի ստորագիր արտահայտությունները՝ մեկ տեղում։",
};

export default function SoundboardPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-7">
      <h1 className="mb-2 font-display text-4xl">Ֆրազների պատ</h1>
      <p className="mb-2 text-muted">
        Կարգինի ամենաստորագիր արտահայտությունները՝ ըստ կրկնվելու հաճախականության։
      </p>
      <p className="mb-8 text-sm text-muted">
        🔊 Ձայնը՝ շուտով — սեղմի՛ր՝ տեսնելու սքեթչը
      </p>
      <Soundboard />
    </main>
  );
}
