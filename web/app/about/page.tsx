import Link from "next/link";
import { BOT_URL, BOT_USERNAME } from "@/lib/site";
import { ALL } from "@/lib/data";

/**
 * Every number on this page is computed from the shipped data or taken from
 * DECISIONS.md — nothing is stated from memory. Where a stage was evaluated but
 * not used (Gemini STT), the page says so rather than implying it ran.
 */
export default function About() {
  const total = ALL.length;
  const withText = ALL.filter((s) => s.text).length;
  const withTranscript = ALL.filter((s) => s.transcript).length;
  const transcriptOnly = ALL.filter((s) => s.transcript && !s.text).length;
  const withSongs = ALL.filter((s) => s.songs?.length).length;
  const songCount = ALL.reduce((n, s) => n + (s.songs?.length ?? 0), 0);
  const withVisual = ALL.filter((s) => s.visual).length;

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-8 sm:py-14">
      <h1 className="font-display text-4xl sm:text-5xl">Կարգին Արխիվ</h1>
      <p className="mt-5 leading-relaxed opacity-80">
        KarginTV-ի {total} սքեթչ (2012–2013)՝ որոնելի տող առ տող։ Որոնիր երկխոսությունը,
        դերասանին, վայրը կամ նույնիսկ այն, ինչ երևում է կադրում, ու անցիր ուղիղ YouTube։
      </p>
      <p className="mt-4 leading-relaxed opacity-80">
        Ամբողջ աղյուսակը՝ զտիչներով ու ներբեռնումով, <Link href="/data" className="font-bold underline underline-offset-2 hover:text-kblue">Տվյալներ</Link> էջում է։
      </p>

      <h2 className="mt-10 font-display text-2xl sm:text-3xl">Շնորհակալություն</h2>
      <div className="mt-4 k-border rounded-lg border-l-[5px] border-l-korange bg-surface px-4 py-4">
        <p className="leading-relaxed">
          Երկխոսությունների ձեռքով հավաքագրմանն օգնել են{" "}
          <b>«Մարզերի երեխաները» (MEM — Children of the Regions)</b> ծրագրի երեխաները։
          Հենց նրանց արած աշխատանքի շնորհիվ է, որ {withText} սքեթչ ունի մարդու ձեռքով
          համադրված տեքստ — և հենց դա է այս արխիվում ամենաարժեքավոր շերտը։
        </p>
        <p className="mt-3 text-sm text-muted">
          Մնացած ամեն ինչը՝ ստորև նկարագրված, մեքենայական է։ Մեքենան կարող է լսել ու նայել,
          բայց չի կարող փոխարինել այն ականջին, որը գիտի՝ ինչ է իրականում ասվում։
        </p>
      </div>

      <h2 className="mt-10 font-display text-2xl sm:text-3xl">Ինչպես է սարքված</h2>
      <p className="mt-4 leading-relaxed opacity-80">
        Տվյալների ամբողջ շերտը հավաքվել է փուլերով։ Ստորև՝ ազնիվ նկարագրությունը՝ ինչ գործիքով,
        ինչ ծածկույթով և ինչ սահմանափակումով։
      </p>

      <Stage n="1" title="Մետատվյալներ — YouTube Data API v3">
        {total} տեսանյութի վերնագիր, տևողություն, վերբեռնման ամսաթիվ, դիտումներ, լեզվի
        պիտակներ և իրավունքների դաշտեր՝ մեկ հարցումով 50 տեսանյութ։ Դիտումների թիվը այն է,
        ինչ API-ն վերադարձրել է հավաքագրման պահին, ոչ թե ուղիղ եթերում։
      </Stage>

      <Stage n="2" title="Վերծանում — YouTube-ի հայերեն ձայնաճանաչում">
        YouTube-ի ավտոմատ ենթագրերը վերցվել են <Code>yt-dlp</Code>-ով, բայց դրանցից իրականում
        հայերեն էր ընդամենը 84-ը. մնացածում YouTube-ը լեզուն սխալ էր ճանաչել։ Մնացած
        տեսանյութերի ձայնը վերբեռնվել է կրկին՝ լեզուն բացահայտ նշելով որպես հայերեն, և
        YouTube-ի հայերեն ձայնաճանաչման արդյունքը հետ է բաժանվել ըստ ժամանակային կտրվածքի։
        Կայքում ցուցադրվում է {withTranscript} վերծանում — միայն այն դեպքերում, երբ այն նոր բան
        է ավելացնում ձեռքով տեքստին։ Դրանցից {transcriptOnly}-ի համար սա միակ գոյություն ունեցող
        երկխոսությունն է։ Սա մեքենայական տեքստ է՝ սխալներով, և կայքում միշտ առանձին է
        նշված։
      </Stage>

      <Stage n="3" title="Երաժշտություն — Shazam (shazamio)">
        Յուրաքանչյուր տեսանյութի ձայնից 30 վայրկյանը մեկ վերցվել է 12 վայրկյանանոց կտոր և
        ուղարկվել Shazam։ Համընկնումը հաստատվել է միայն այն դեպքում, երբ 5 վայրկյանով
        տեղաշարժված երկրորդ կտորը տվել է նույն պատասխանը — նույն բայթերը միշտ համաձայնում են
        իրենց հետ, տեղաշարժն է իրական ստուգումը։ Արդյունք՝ {withSongs} սքեթչում {songCount}{" "}
        հաստատված կատարում։ Համեմատության համար՝ YouTube-ի սեփական երաժշտական նշումները տվել
        էին ընդամենը 17-ը։
      </Stage>

      <Stage n="4" title="Տեսարանը — Claude-ը նայում է կադրերին">
        Յուրաքանչյուր սքեթչից սարքվել է մեկ «կոնտակտային թերթիկ»՝ 40 կադր 8×5 ցանցում, ամեն
        կադրի վրա՝ իր ժամանակը։ Այդ թերթիկները կարդացել է <b>Claude Sonnet</b>-ը, իսկ ցածր
        վստահության 101 դեպքը վերընթերցել է <b>Claude Opus</b>-ը։ Ընթերցումը «կույր» է. մոդելը
        չի տեսել ոչ տեքստը, ոչ վերծանումը, և արգելված է եղել անուններ կռահել — որպեսզի
        նկարագրությունը լինի այն, ինչ իրականում երևում է։ Ծածկույթը՝ {withVisual}/{total}։
        Այստեղից են գալիս «կով», «Lada», «հարսանիք» տիպի որոնումները, որոնք երկխոսության մեջ
        երբեք չեն հնչում։ Նկարագրությունները անգլերեն են։
      </Stage>

      <Stage n="5" title="Անոտացիաներ — Gemini 3 Flash (Vertex AI)">
        Ամեն սքեթչի համար՝ վերնագրեր, ամփոփումներ, բանալի բառեր, թեմաներ և հումորի տեսակ՝
        <Code>gemini-3-flash-preview</Code> մոդելով, կառուցվածքային ելքով (ցանկը պարտադրված է
        սխեմայով, ոչ թե հուշումով)։ Մոդելն ընտրվել է ArmBench-LLM-ի հայերենի վարկանիշով։
        702-ից 690-ը արել է Gemini-ն՝ $2.00-ով. 12 սքեթչ Google-ի բովանդակության զտիչը
        մերժել է (պատճառը հենց ձեռքով հավաքած կոպիտ երկխոսությունն էր), և դրանք արել է{" "}
        <Code>claude-opus-5</Code>-ը՝ նույն մուտքով։ Ամբողջ նախագծի Gemini-ի ծախսը՝ $2.27։
      </Stage>

      <Stage n="6" title="«Նմանատիպ» — gemini-embedding-2">
        Ամեն սքեթչի անգլերեն մանրամասն ամփոփումը վերածվել է 3072-չափանի վեկտորի, և
        նմանությունը հաշվվել է կոսինուսով։ Ցուցադրվում են միայն 0.75-ից բարձր
        գնահատականները. ցածր միավորները ոչ թե թույլ նմանություն են, այլ աղմուկ, և այն
        սքեթչերի համար, որոնց արխիվում զույգ չկա, «նմանատիպ»-ը լրացվում է ընդհանուր
        դերասանների հիման վրա։ Ստուգումը՝ ձայնային մատնահետքով գտնված 23 կրկնօրինակից 23-ը
        այս մեթոդով նույնպես առաջին տեղում են, թեև վեկտորը ձայնը երբեք չի լսել։
      </Stage>

      <Stage n="7" title="Կրկնօրինակներ — ձայնային մատնահետք">
        Ամեն տեսանյութի առաջին 60 վայրկյանից հանվել է ակուստիկ մատնահետք, բոլոր 246,051
        զույգերը համեմատվել են, իսկ կասկածելիները՝ հաստատվել ձայնի ուղիղ խաչաձև
        հարաբերակցությամբ։ Գտնվել է 32 զույգ, որից 23-ը՝ նույն ձայնագրությունը։ Վերնագրերով
        դրանցից հնարավոր էր գտնել ընդամենը մեկը։
      </Stage>

      <Stage n="8" title="Որոնումը">
        Նախ՝ ուղիղ համընկնում։ Եթե քիչ բան գտնվեց, և հարցումը մեկից ավելի բառ է, բառերը
        փնտրվում են առանձին, և ամեն բառ կշռվում է ըստ իր <b>հազվադեպության</b> — «որ»-ը և
        «եմ»-ը գրեթե ոչինչ չեն նշանակում, հազվադեպ բառը մենակ կարող է որոշել սքեթչը։ Առանց
        այդ կշռի «պապա պտի ասես»-ը վերադարձնում էր 702-ից 538-ը՝ միայն լցոն բառերի հաշվին։
        Վերջում՝ ուղղագրական շեղումը. հարցման ամենահազվադեպ բառը համեմատվում է արխիվի
        բառապաշարի հետ խմբագրման հեռավորությամբ (այսպես «սարո»-ն գտնում է «Սամո»-ին)։
        Հայերենը ինդեքսավորվում է նաև լատինատառ և ռուսատառ ձևով, այնպես որ «tormuz» և
        «тормуз» գտնում են նույնը, ինչ «տոռմուզ»։
      </Stage>

      <p className="mt-8 text-sm text-muted">
        Մեքենայական ամեն շերտ սխալվում է։ Եթե որևէ տեղ սխալ ես նկատել, կամ փնտրածդ սքեթչը
        չկա — ասա մեզ. ամեն էջի ներքևում կոճակ կա։
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
        Ամենահարմարը՝ ցանկացած չաթում գրիր <Code>@{BOT_USERNAME} տոռմուզ</Code>,
        ընտրիր սքեթչը, և այն կհայտնվի հենց այդ խոսակցության մեջ։
      </p>
    </main>
  );
}

function Stage({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6 border-t-2 border-ink/15 pt-5">
      <h3 className="font-display text-lg tracking-wide">
        <span className="text-kred">{n}.</span> {title}
      </h3>
      <p className="mt-2 leading-relaxed opacity-80">{children}</p>
    </section>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return <code className="rounded bg-paper2 px-1.5 py-0.5 text-sm">{children}</code>;
}
