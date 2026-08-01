/**
 * User-facing changelog. Newest first.
 *
 * Deliberately hand-written rather than generated from git: commit messages are
 * written for whoever maintains the code, and most commits change nothing a
 * visitor would notice. Only what is visible on the site belongs here.
 *
 * `count` is resolved at build time from the real data (see the page), so
 * figures cannot drift out of date as the archive fills in.
 */
export interface ChangelogItem {
  /** Emoji shown next to the line. */
  icon: string;
  text: string;
  /** Which live figure to append, if any. */
  count?: "songs" | "sketchesWithSongs" | "sketches" | "withText";
}

export interface ChangelogEntry {
  date: string;          // YYYY-MM-DD
  title: string;
  items: ChangelogItem[];
}

export const CHANGELOG: ChangelogEntry[] = [
  {
    date: "2026-08-02",
    title: "Երաժշտություն և ամբողջական տեքստ",
    items: [
      {
        icon: "🎵",
        text: "Սքեթչի էջում այժմ երևում է, թե ինչ երաժշտություն է հնչում — կատարող, ալբոմի պիտակ, տարեթիվ և ժամանակի նշումներ, որոնք տանում են ուղիղ YouTube-ի այդ վայրկյանին։ Ճանաչված է ձայնից",
        count: "sketchesWithSongs",
      },
      {
        icon: "💬",
        text: "Քարտերում այժմ երևում է ամբողջ երկխոսությունը, ոչ թե մեկ տողը",
      },
      {
        icon: "🔍",
        text: "Որոնելիս համընկնող տողերը ընդգծվում են և բարձրանում վերև, որ երևա՝ ինչու է սքեթչը գտնվել",
      },
    ],
  },
  {
    date: "2026-08-01",
    title: "Կրկնօրինակներ և ավելի շատ տվյալ",
    items: [
      {
        icon: "🔁",
        text: "Ձայնի «մատնահետքով» գտնվեցին նույն սքեթչի կրկնված վերբեռնումները — 23 զույգ, և 4 դեպք, երբ երկար տեսանյութը պարունակում է կարճը",
      },
      {
        icon: "🗂",
        text: "Արխիվի մետատվյալները ընդլայնվեցին (հավանումներ, մեկնաբանություններ, տարածաշրջանային սահմանափակումներ)",
      },
    ],
  },
  {
    date: "2026-06-22",
    title: "Արագացում",
    items: [
      {
        icon: "⚡",
        text: "Էջի տվյալները թեթևացան 2.8 ՄԲ-ից մինչև 1.6 ՄԲ — որոնումը նկատելիորեն արագացավ հեռախոսի վրա",
      },
    ],
  },
  {
    date: "2026-06-16",
    title: "Մութ թեմա, ֆրազներ, դերասաններ",
    items: [
      { icon: "🌙", text: "Մութ թեմա (կոճակը՝ վերևի աջ անկյունում)" },
      { icon: "🔊", text: "Ֆրազների պատ — 12 հանրահայտ արտահայտություն" },
      { icon: "🎭", text: "Դերասանների էջեր — վիճակագրություն, գործընկերներ, բնորոշ տողեր" },
      { icon: "❓", text: "Քուիզ՝ մակարդակներով" },
      { icon: "📊", text: "Վիճակագրության էջ" },
      { icon: "🙋", text: "«Իմ անունը» — գտիր, թե որ սքեթչներում է հնչում քո անունը" },
      { icon: "⌨️", text: "Որոնում լատինատառ և կիրիլիցայով — գրիր tormuz կամ тормуз" },
    ],
  },
  {
    date: "2026-06-16",
    title: "Կայքի մեկնարկը",
    items: [
      { icon: "🚀", text: "Կարգին Արխիվը հասանելի դարձավ", count: "sketches" },
      { icon: "📝", text: "Ձեռքով համադրված երկխոսություններ", count: "withText" },
    ],
  },
];
