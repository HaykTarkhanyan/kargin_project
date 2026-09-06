import { BOT_URL, BOT_USERNAME } from "@/lib/site";

export default function About() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-8 sm:py-14">
      <h1 className="font-display text-4xl sm:text-5xl">Կարգին Արխիվ</h1>
      <p className="mt-5 leading-relaxed opacity-80">
        KarginTV-ի 702 սքեթչ (2012–2013), ձեռքով համադրված տեքստերով։ Որոնիր երկխոսությունը,
        դերասանին կամ վայրը, ու անցիր ուղիղ YouTube։
      </p>
      <p className="mt-4 leading-relaxed opacity-80">
        Տվյալները՝ ձեռքով կուրացված + YouTube Data API։ ~602 սքեթչ ունի համադրված տեքստ. մնացածի
        ամբողջական որոնումը կգա ձայնի տրանսկրիպցիայից հետո։
      </p>
      <h2 className="mt-10 font-display text-2xl sm:text-3xl">Telegram բոտ</h2>
      <p className="mt-4 leading-relaxed opacity-80">
        Նույն որոնումը կա նաև Telegram-ում՝{" "}
        <a href={BOT_URL} target="_blank" rel="noreferrer" className="font-bold underline underline-offset-2 hover:text-kblue">
          @{BOT_USERNAME}
        </a>
        ։ Գրիր ռեպլիկան, ստացիր սքեթչը՝ հենց չաթում նվագարկվող տեսանյութով։
      </p>
      <p className="mt-4 leading-relaxed opacity-80">
        Ամենահարմարը՝ ցանկացած չաթում գրիր <code className="rounded bg-paper2 px-1.5 py-0.5 text-sm">@{BOT_USERNAME} տոռմուզ</code>,
        ընտրիր սքեթչը, և այն կհայտնվի հենց այդ խոսակցության մեջ։
      </p>
    </main>
  );
}
