/**
 * Quiz data (dummy for now). Shaped so it can later be generated from a CSV.
 * Levels are ordered easy → hard; passing one unlocks the next (see QuizGame).
 */
export interface QuizQuestion {
  prompt: string;
  options: string[];
  correctIndex: number;
  explanation?: string;
}

export interface Quiz {
  id: string;
  level: number;
  title: string;
  difficulty: string;
  passPct: number; // fraction correct needed to pass (tunable)
  questions: QuizQuestion[];
}

export const QUIZZES: Quiz[] = [
  {
    id: "l1-basics",
    level: 1,
    title: "Կարգինի հիմունքները",
    difficulty: "Հեշտ",
    passPct: 0.6,
    questions: [
      { prompt: "Քանի՞ սքեթչ կա արխիվում", options: ["302", "702", "1002", "1502"], correctIndex: 1, explanation: "Ճիշտ 702 սքեթչ։" },
      { prompt: "Ո՞ր տարիներին են ստեղծվել սքեթչները", options: ["2008–2009", "2012–2013", "2016–2017", "2020–2021"], correctIndex: 1, explanation: "2012 հունիս – 2013 ապրիլ։" },
      { prompt: "Ովքե՞ր են գլխավոր դերասանները", options: ["Հայկո և Մկո", "Աշոտ և Անդո", "Ռաֆո և Սաքո", "Գագո և Կարո"], correctIndex: 0, explanation: "Հայկո-ն ու Մկո-ն՝ սքեթչների ~76%-ում։" },
      { prompt: "Ո՞ր արտահայտությունն է ամենահաճախ հնչում", options: ["«բարև ձեզ»", "«շատ լավ»", "«ցավդ տանեմ»", "«ոնց ես»"], correctIndex: 2, explanation: "«ցավդ տանեմ»՝ 257 անգամ։" },
      { prompt: "Մոտավորապես ի՞նչ միջին տևողություն ունեն սքեթչները", options: ["~1 րոպե", "~3 րոպե", "~7 րոպե", "~12 րոպե"], correctIndex: 1, explanation: "Միջինը 2:54։" },
    ],
  },
  {
    id: "l2-numbers",
    level: 2,
    title: "Թվերն ու փաստերը",
    difficulty: "Միջին",
    passPct: 0.6,
    questions: [
      { prompt: "Ո՞ր դերասանն ունի ամենաբարձր ՄԻՋԻՆ դիտում մեկ սքեթչում", options: ["Հայկո", "Մկո", "Ռաֆո", "Հասմիկ"], correctIndex: 2, explanation: "Ռաֆո՝ ընդամենը 22 սքեթչ, բայց միջինը 1.06M դիտում։" },
      { prompt: "Ո՞ր վայրն է ամենաշատ հանդիպում (բացի «Այլ»-ից)", options: ["Խանութ", "Տուն", "Հիվանդանոց", "Գրասենյակ"], correctIndex: 1, explanation: "Տուն՝ 155 սքեթչ։" },
      { prompt: "Ո՞ր սքեթչն է ամենաշատ դիտվածը", options: ["սքեթչ 582", "Remont", "սքեթչ 424", "սքեթչ 228"], correctIndex: 0, explanation: "սքեթչ 582՝ 6.0M դիտում։" },
      { prompt: "Որքա՞ն է արխիվի ընդհանուր տևողությունը", options: ["~12 ժամ", "~34 ժամ", "~70 ժամ", "~120 ժամ"], correctIndex: 1, explanation: "33.9 ժամ։" },
      { prompt: "Հայերենից հետո ո՞ր լեզուն է երկրորդը երկխոսություններում", options: ["անգլերեն", "ռուսերեն", "թուրքերեն", "ֆրանսերեն"], correctIndex: 1, explanation: "Ռուսերեն՝ 19 սքեթչում։" },
    ],
  },
  {
    id: "l3-expert",
    level: 3,
    title: "Իսկական գիտակ",
    difficulty: "Բարդ",
    passPct: 0.6,
    questions: [
      { prompt: "«արա էսի ուզբեկ ա» — ո՞ր սքեթչից է", options: ["սքեթչ 285", "սքեթչ 663", "սքեթչ 487", "սքեթչ 108"], correctIndex: 1, explanation: "սքեթչ 663-ից (Տուն, 1.4M դիտում)։" },
      { prompt: "Ո՞ր արտահայտությունն է ԵՐԿՐՈՐԴ ամենահաճախը", options: ["«ախպեր ջան»", "«բարև ձեզ»", "«տղա ջան»", "«շատ լավ»"], correctIndex: 0, explanation: "«ախպեր ջան»՝ 216 անգամ (1-ինը՝ «ցավդ տանեմ»)։" },
      { prompt: "Ո՞րն է ամենաերկար սքեթչը", options: ["~12 րոպե", "~16 րոպե", "~19.5 րոպե", "~25 րոպե"], correctIndex: 2, explanation: "Ամենաերկարը՝ 19:37։" },
      { prompt: "Քանի՞ սքեթչ ունի ձեռքով համադրված երկխոսություն", options: ["402", "502", "602", "702"], correctIndex: 2, explanation: "602 սքեթչ ունի տեքստ (մնացածը՝ տրանսկրիպցիայից հետո)։" },
      { prompt: "Հայկո-ն ու Մկո-ն միասին քանի՞ սքեթչում են", options: ["274", "474", "574", "674"], correctIndex: 1, explanation: "474 սքեթչում միասին։" },
    ],
  },
];
