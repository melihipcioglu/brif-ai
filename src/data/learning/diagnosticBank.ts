import type { DiagnosticQuestion } from '../../types/learning';

export const DIAGNOSTIC_QUESTIONS_BANK: readonly DiagnosticQuestion[] = [
  // 1. VOCAB RECOGNITION (Temel Fen Sözcükleri)
  {
    id: 'DIAG_VOCAB_01',
    type: 'VOCAB_RECOGNITION',
    prompt: '"prevent" kelimesinin fen bilimlerindeki en temel Türkçe karşılığı nedir?',
    options: [
      {
        id: 'A',
        text: 'engellemek, önlemek',
        isCorrect: true,
        feedback: 'Harika! "Prevent", bir sürecin ya da hastalığın ortaya çıkmasını önlemek/engellemek anlamına gelir.'
      },
      {
        id: 'B',
        text: 'tercih etmek',
        isCorrect: false,
        feedback: '"Tercih etmek" İngilizcede "prefer" kelimesidir. "Prevent" engellemek demektir.'
      },
      {
        id: 'C',
        text: 'kanıtlamak',
        isCorrect: false,
        feedback: '"Kanıtlamak" İngilizcede "prove" kelimesidir.'
      },
      {
        id: 'D',
        text: 'tahmin etmek',
        isCorrect: false,
        feedback: '"Tahmin etmek" İngilizcede "predict" kelimesidir.'
      }
    ],
    scaffoldTip: 'Pre- (önce) kökünden aklınızda tutun: Önceden engel olmak.'
  },
  {
    id: 'DIAG_VOCAB_02',
    type: 'VOCAB_RECOGNITION',
    prompt: '"increase" kelimesi fen deneylerinde ve grafiklerde neyi ifade eder?',
    options: [
      {
        id: 'A',
        text: 'azalma, düşüş',
        isCorrect: false,
        feedback: '"Azalma" İngilizcede "decrease" kelimesidir.'
      },
      {
        id: 'B',
        text: 'artış, çoğalma',
        isCorrect: true,
        feedback: 'Doğru! "Increase" yukarı yönlü artışı ve çoğalmayı temsil eder.'
      },
      {
        id: 'C',
        text: 'sabit kalma',
        isCorrect: false,
        feedback: '"Sabit kalma" İngilizcede "remain constant" veya "stabilize" ile ifade edilir.'
      },
      {
        id: 'D',
        text: 'yok olma',
        isCorrect: false,
        feedback: '"Yok olma" İngilizcede "disappear" veya "vanish" kelimesidir.'
      }
    ],
    scaffoldTip: 'Ok yukarı yönlüdür: In-crease (artış) ↔ De-crease (azalış).'
  },
  {
    id: 'DIAG_VOCAB_03',
    type: 'VOCAB_RECOGNITION',
    prompt: '"absorb" fiili biyoloji ve kimya bağlamında hangi anlama gelir?',
    options: [
      {
        id: 'A',
        text: 'emmek, içine çekmek',
        isCorrect: true,
        feedback: 'Doğru! Bitkilerin suyu emmesi veya dokuların ışığı/ısıyı soğurması (absorb) anlamındadır.'
      },
      {
        id: 'B',
        text: 'yansıtmak',
        isCorrect: false,
        feedback: '"Yansıtmak" İngilizcede "reflect" kelimesidir. Absorb tam tersidir (içine çeker).'
      },
      {
        id: 'C',
        text: 'salgılamak',
        isCorrect: false,
        feedback: '"Salgılamak" İngilizcede "secrete" veya "release" kelimesidir.'
      },
      {
        id: 'D',
        text: 'parçalamak',
        isCorrect: false,
        feedback: '"Parçalamak" İngilizcede "break down" veya "degrade" kelimesidir.'
      }
    ],
    scaffoldTip: 'Türkçedeki "absorbe etmek" ifadesinden doğrudan hatırlayabilirsiniz.'
  },
  {
    id: 'DIAG_VOCAB_04',
    type: 'VOCAB_RECOGNITION',
    prompt: '"observe" kelimesi bir bilim insanının laboratuvardaki hangi temel eylemidir?',
    options: [
      {
        id: 'A',
        text: 'ihmal etmek',
        isCorrect: false,
        feedback: '"İhmal etmek" İngilizcede "neglect" veya "ignore" kelimesidir.'
      },
      {
        id: 'B',
        text: 'gözlemlemek, fark etmek',
        isCorrect: true,
        feedback: 'Doğru! Bilimsel yöntemin ilk adımı olan "gözlem yapmak" (observe) fiilidir.'
      },
      {
        id: 'C',
        text: 'tartışmak',
        isCorrect: false,
        feedback: '"Tartışmak" İngilizcede "discuss" veya "debate" kelimesidir.'
      },
      {
        id: 'D',
        text: 'şüphelenmek',
        isCorrect: false,
        feedback: '"Şüphelenmek" İngilizcede "suspect" veya "doubt" kelimesidir.'
      }
    ],
    scaffoldTip: 'Observation = Gözlem. Bilimsel deneylerin vazgeçilmez temel kelimesidir.'
  },

  // 2. SYNTAX IDENTIFICATION (Cümle İskeleti: Özne ve Fiil Tespiti)
  {
    id: 'DIAG_SYNTAX_01',
    type: 'SYNTAX_IDENTIFICATION',
    sentence: 'Photosynthetic plants convert sunlight into chemical energy.',
    prompt: 'Yukarıdaki cümlenin ANA FİİLİ (yüklemi / temel eylemi) hangisidir?',
    options: [
      {
        id: 'A',
        text: 'Photosynthetic',
        isCorrect: false,
        feedback: '"Photosynthetic", cümlenin öznesi olan "plants" kelimesini niteleyen bir sıfattır.'
      },
      {
        id: 'B',
        text: 'plants',
        isCorrect: false,
        feedback: '"plants" bu cümlenin öznesidir (eylemi yapan bitkiler).'
      },
      {
        id: 'C',
        text: 'convert',
        isCorrect: true,
        feedback: 'Mükemmel! Cümlenin kalbi "convert" (dönüştürmek) fiilidir. Bitkiler güneş ışığını dönüştürür.'
      },
      {
        id: 'D',
        text: 'energy',
        isCorrect: false,
        feedback: '"energy" cümlenin nesnesidir (dönüştürülen şey).'
      }
    ],
    scaffoldTip: 'Özneden hemen sonra gelen zaman çekimli eyleme odaklanın: Özne (Plants) + Fiil (convert).'
  },
  {
    id: 'DIAG_SYNTAX_02',
    type: 'SYNTAX_IDENTIFICATION',
    sentence: 'Extreme temperatures can damage cellular membranes.',
    prompt: 'Bu cümlede eylemi gerçekleştiren ÖZNE grubu hangisidir?',
    options: [
      {
        id: 'A',
        text: 'Extreme temperatures',
        isCorrect: true,
        feedback: 'Doğru! Cümlenin öznesi "Aşırı sıcaklıklar" (Extreme temperatures) grubudur.'
      },
      {
        id: 'B',
        text: 'can damage',
        isCorrect: false,
        feedback: '"can damage" cümlenin modal destekli fiilidir (zarar verebilir).'
      },
      {
        id: 'C',
        text: 'cellular membranes',
        isCorrect: false,
        feedback: '"cellular membranes" eylemden etkilenen nesnedir (hücre zarları).'
      },
      {
        id: 'D',
        text: 'damage',
        isCorrect: false,
        feedback: '"damage" fiildir.'
      }
    ],
    scaffoldTip: 'Fiilden (can damage) önce gelen tüm isim tamlaması cümlenin öznesidir.'
  },
  {
    id: 'DIAG_SYNTAX_03',
    type: 'SYNTAX_IDENTIFICATION',
    sentence: 'Water pollution directly threatens aquatic ecosystems.',
    prompt: '"directly" kelimesi bu cümlede hangi görevi üstlenmiştir?',
    options: [
      {
        id: 'A',
        text: 'Zarf (Fiili niteleyen: doğrudan/doğrudan doğruya)',
        isCorrect: true,
        feedback: 'Doğru! -ly eki alan kelimeler fiilin nasıl yapıldığını niteleyen zarflardır (threatens fiilini niteliyor).'
      },
      {
        id: 'B',
        text: 'Cümlenin ana öznesi',
        isCorrect: false,
        feedback: 'Özne "Water pollution" (Su kirliliği) tamlamasıdır.'
      },
      {
        id: 'C',
        text: 'Cümlenin ana fiili',
        isCorrect: false,
        feedback: 'Ana fiil "threatens" (tehdit eder) kelimesidir.'
      },
      {
        id: 'D',
        text: 'Cümlenin nesnesi',
        isCorrect: false,
        feedback: 'Nesne "aquatic ecosystems" (sucul ekosistemler) grubudur.'
      }
    ],
    scaffoldTip: '-ly eki genellikle eylemin nasıl gerçekleştiğini anlatan zarfları (adverb) işaret eder.'
  },

  // 3. CONNECTOR DIRECTION (Bağlaç ve Düşünce Akışı)
  {
    id: 'DIAG_CONN_01',
    type: 'CONNECTOR_DIRECTION',
    sentence: '____ solar panels are expensive to install, they save substantial energy in the long term.',
    prompt: 'İki cümle arasındaki anlam ilişkisine göre (Maliyetli olmasına RAĞMEN / Uzun vadede tasarruf sağlar) başa hangi bağlaç gelmelidir?',
    options: [
      {
        id: 'A',
        text: 'Although (E rağmen - Zıtlık)',
        isCorrect: true,
        feedback: 'Tebrikler! Olumsuz bir durum (pahalı) ile olumlu bir sonucu (tasarruf sağlar) bağlayan zıtlık bağlacıdır.'
      },
      {
        id: 'B',
        text: 'Because (Çünkü - Sebep)',
        isCorrect: false,
        feedback: '"Because" sebep bildirir. Pahalı olduğu için tasarruf sağlamaz; pahalı olmasına RAĞMEN sağlar.'
      },
      {
        id: 'C',
        text: 'Unless (Medikçe - Olumsuz Koşul)',
        isCorrect: false,
        feedback: '"Unless" olumsuz koşul bağlacıdır; buradaki zıtlık ilişkisine uymaz.'
      },
      {
        id: 'D',
        text: 'Therefore (Bu yüzden - Sonuç)',
        isCorrect: false,
        feedback: '"Therefore" iki bağımsız cümlenin arasında geçiş zarfı olarak kullanılır; cümlenin başına bu yapıyla gelmez.'
      }
    ],
    scaffoldTip: 'Zıtlık formülü: [- Olumsuz Özellik] + [Although] + [+ Olumlu Sonuç].'
  },
  {
    id: 'DIAG_CONN_02',
    type: 'CONNECTOR_DIRECTION',
    sentence: 'The experiment was terminated ____ toxic gases were released unexpectedly.',
    prompt: 'Deney sonlandırıldı (Sonuç) ____ zehirli gazlar beklenmedik şekilde açığa çıktı (Sebep). Boşluğa ne gelmelidir?',
    options: [
      {
        id: 'A',
        text: 'because (çünkü - sebep)',
        isCorrect: true,
        feedback: 'Doğru! Deneyin durdurulmasının açık nedenini açıklayan sebep bağlacıdır.'
      },
      {
        id: 'B',
        text: 'although (rağmen - zıtlık)',
        isCorrect: false,
        feedback: 'Gaz açığa çıkmasına rağmen durdurulmadı değil, gaz çıktığı İÇİN durduruldu.'
      },
      {
        id: 'C',
        text: 'despite (e rağmen - isim alır)',
        isCorrect: false,
        feedback: '"Despite" ardından tam cümle (toxic gases were released) alamaz; isim öbeği alır.'
      },
      {
        id: 'D',
        text: 'whereas (oysa/halbuki - karşılaştırma)',
        isCorrect: false,
        feedback: '"Whereas" iki farklı durumu zıt yönde karşılaştırır; sebep-sonuç bağlamaz.'
      }
    ],
    scaffoldTip: 'Sebep-Sonuç ilişkisi: Sonuç (Terminated) + BECAUSE + Sebep (Gases released).'
  }
];
