import type { AcademicReadingPassage } from '../../types/learning';

export const academicReadingBank: readonly AcademicReadingPassage[] = [
  {
    id: 'reading-passage-1-neuro',
    title: 'Nörodejeneratif Süreçler ve Protein Baskılama',
    science_domain: 'medicine',
    target_words: ['inhibit', 'susceptible', 'deteriorate', 'trigger'],
    main_idea_tr:
      'Yaşlanan beyinde zararlı proteinlerin birikimi nöronal yapıları savunmasız bırakmakta ve sinaptik bozulmayı tetiklemektedir; ancak yeni moleküller bu süreci baskılamayı amaçlamaktadır.',
    paragraph_text:
      'Although the human central nervous system possesses remarkable neuroplasticity, aging neural tissues become increasingly susceptible to oxidative stress. When toxic protein aggregates accumulate in the synaptic cleft, they trigger a cascade of neuroinflammatory responses. As a consequence, cognitive function may deteriorate progressively over several years. Therefore, recent pharmacological trials focus on synthetic molecules designed to inhibit this pathological accumulation before irreversible neuronal loss occurs.',
    sentences: [
      {
        id: 's1-neuro',
        sentence:
          'Although the human central nervous system possesses remarkable neuroplasticity, aging neural tissues become increasingly susceptible to oxidative stress.',
        translation_tr:
          'İnsan merkezi sinir sistemi dikkate değer bir nöroplastisiteye sahip olmasına rağmen, yaşlanan sinir dokuları oksidatif strese karşı giderek daha savunmasız hale gelir.',
        science_domain: 'medicine',
        target_word_ids: ['susceptible'],
        pedagogical_focus: 'CLAUSE_DECOMPOSITION',
        pedagogical_tip_tr:
          '"Although" zıtlık bağlacı yan cümleyi (possesses neuroplasticity - olumlu) ana cümleden (become susceptible - olumsuz) ayırır. Özne: "aging neural tissues", Temel Fiil: "become".',
        tokens: [
          { text: 'Although', role: 'CONNECTOR', explanation_tr: 'Zıtlık/ödün bağlacı (rağmen). Beklentinin aksine bir durum başlatır.' },
          { text: 'the human central nervous system', role: 'SUBJECT', explanation_tr: 'Yan cümlenin öznesi (insan merkezi sinir sistemi).' },
          { text: 'possesses', role: 'VERB', explanation_tr: 'Yan cümlenin fiili (sahiptir).' },
          { text: 'remarkable neuroplasticity,', role: 'OBJECT', explanation_tr: 'Yan cümlenin nesnesi (dikkate değer nöroplastisite).' },
          { text: 'aging neural tissues', role: 'SUBJECT', explanation_tr: 'ANA CÜMLENİN ÖZNESİ (yaşlanan sinir dokuları).' },
          { text: 'become', role: 'VERB', explanation_tr: 'ANA CÜMLENİN TEMEL FİİLİ (hale gelir / dönüşür).' },
          { text: 'increasingly', role: 'MODIFIER', explanation_tr: 'Zarf: derecesini belirtir (giderek artan şekilde).' },
          { text: 'susceptible', role: 'TARGET_WORD', explanation_tr: 'HEDEF KELİME: savunmasız, açık, duyarlı (susceptible to).', isTargetWord: true },
          { text: 'to oxidative stress.', role: 'MODIFIER', explanation_tr: 'Edat öbeği: neye karşı savunmasız olduğunu tamamlar.' }
        ],
        main_clause: {
          subject: 'aging neural tissues',
          verb: 'become',
          object: 'increasingly susceptible to oxidative stress'
        },
        subordinate_clause: {
          connector: 'Although',
          clause: 'the human central nervous system possesses remarkable neuroplasticity',
          function_tr: 'Ana cümlenin zıddı bir ön kabul sunan ödün (concession) zarf tümleci.'
        },
        interactive_question: {
          prompt: 'Bu cümlenin ana yüklemi (main finite verb) aşağıdakilerden hangisidir?',
          options: ['possesses', 'become', 'aging', 'susceptible'],
          correct_index: 1,
          rationale_tr:
            '"possesses" Although yan cümlesinin yüklemidir. Cümlenin asıl mesajını taşıyan ana yüklem "become" fiilidir.'
        }
      },
      {
        id: 's2-neuro',
        sentence:
          'When toxic protein aggregates accumulate in the synaptic cleft, they trigger a cascade of neuroinflammatory responses.',
        translation_tr:
          'Toksik protein kümeleri sinaptik aralıkta biriktiğinde, nöroenflamatuar yanıtlar dizisini tetiklerler.',
        science_domain: 'medicine',
        target_word_ids: ['trigger'],
        pedagogical_focus: 'SUBJECT_VERB_IDENTIFICATION',
        pedagogical_tip_tr:
          '"When" zaman bağlacı tetikleyici koşulu belirtir. Ana cümlenin öznesi "they" (protein aggregates), ana yüklemi "trigger" (tetikler).',
        tokens: [
          { text: 'When', role: 'CONNECTOR', explanation_tr: 'Zaman bağlacı (-dığında). Koşul/zaman bildiren yan cümleyi başlatır.' },
          { text: 'toxic protein aggregates', role: 'SUBJECT', explanation_tr: 'Yan cümlenin öznesi (toksik protein kümeleri).' },
          { text: 'accumulate', role: 'VERB', explanation_tr: 'Yan cümlenin fiili (birikmek).' },
          { text: 'in the synaptic cleft,', role: 'MODIFIER', explanation_tr: 'Yer bildiren edat tümleci (sinaptik yarıkta).' },
          { text: 'they', role: 'SUBJECT', explanation_tr: 'ANA CÜMLENİN ÖZNESİ (protein kümelerine gönderimde bulunan zamir).' },
          { text: 'trigger', role: 'TARGET_WORD', explanation_tr: 'ANA CÜMLENİN TEMEL FİİLİ: tetiklemek, başlatmak.', isTargetWord: true },
          { text: 'a cascade of neuroinflammatory responses.', role: 'OBJECT', explanation_tr: 'Nesne grubu (nöroenflamatuar yanıtlar zinciri).' }
        ],
        main_clause: {
          subject: 'they (toxic protein aggregates)',
          verb: 'trigger',
          object: 'a cascade of neuroinflammatory responses'
        },
        subordinate_clause: {
          connector: 'When',
          clause: 'toxic protein aggregates accumulate in the synaptic cleft',
          function_tr: 'Tetikleyici koşulun gerçekleştiği zamanı bildiren yan cümle.'
        },
        interactive_question: {
          prompt: '"they" zamiri metinde hangi ögeye gönderme yapmaktadır?',
          options: ['neural tissues', 'toxic protein aggregates', 'synaptic cleft', 'stress'],
          correct_index: 1,
          rationale_tr:
            '"When" yan tümcesindeki çoğul özne "toxic protein aggregates", ana cümlede "they" zamiri ile yinelenmiştir.'
        }
      },
      {
        id: 's3-neuro',
        sentence:
          'As a consequence, cognitive function may deteriorate progressively over several years.',
        translation_tr:
          'Bunun bir sonucu olarak, bilişsel fonksiyon birkaç yıl boyunca giderek kötüleşebilir.',
        science_domain: 'medicine',
        target_word_ids: ['deteriorate'],
        pedagogical_focus: 'CONNECTOR_DISCOURSE',
        pedagogical_tip_tr:
          '"As a consequence" geçiş ifadesi önceki cümlenin sebep olduğu neticeyi bildirir. Yüklem: "may deteriorate" (kötüleşebilir).',
        tokens: [
          { text: 'As a consequence,', role: 'CONNECTOR', explanation_tr: 'Söylem bağlacı: sonuç olarak, netice itibarıyla.' },
          { text: 'cognitive function', role: 'SUBJECT', explanation_tr: 'Özne: bilişsel işlev.' },
          { text: 'may', role: 'VERB', explanation_tr: 'Modal: olasılık bildirir (-ebilir).' },
          { text: 'deteriorate', role: 'TARGET_WORD', explanation_tr: 'HEDEF KELİME: kötüleşmek, kalitesi bozulmak.', isTargetWord: true },
          { text: 'progressively', role: 'MODIFIER', explanation_tr: 'Zarf: kademeli olarak, adım adım.' },
          { text: 'over several years.', role: 'MODIFIER', explanation_tr: 'Zaman edatı: birkaç yıllık bir süreç boyunca.' }
        ],
        main_clause: {
          subject: 'cognitive function',
          verb: 'may deteriorate'
        },
        interactive_question: {
          prompt: '"As a consequence" ifadesinin yerine anlamı bozmadan hangi bağlaç getirilebilir?',
          options: ['Conversely', 'Consequently', 'Nevertheless', 'On the contrary'],
          correct_index: 1,
          rationale_tr:
            '"As a consequence" ve "Consequently" her ikisi de neden-sonuç zincirinde "sonuç olarak" anlamı taşır.'
        }
      },
      {
        id: 's4-neuro',
        sentence:
          'Therefore, recent pharmacological trials focus on synthetic molecules designed to inhibit this pathological accumulation before irreversible neuronal loss occurs.',
        translation_tr:
          'Bu nedenle, son farmakolojik denemeler, geri döndürülemez nöronal kayıp gerçekleşmeden önce bu patolojik birikimi engellemek için tasarlanmış sentetik moleküllere odaklanmaktadır.',
        science_domain: 'medicine',
        target_word_ids: ['inhibit'],
        pedagogical_focus: 'RELATIVE_CLAUSE_UNPACKING',
        pedagogical_tip_tr:
          '"designed to inhibit" yapısı bir kısaltılmış sıfat fiildir (which are designed to inhibit). Amacı: patolojik birikimi engellemek.',
        tokens: [
          { text: 'Therefore,', role: 'CONNECTOR', explanation_tr: 'Neden-sonuç bağlacı (Bu yüzden / Dolayısıyla).' },
          { text: 'recent pharmacological trials', role: 'SUBJECT', explanation_tr: 'ÖZNE: son farmakolojik denemeler.' },
          { text: 'focus on', role: 'VERB', explanation_tr: 'YÜKLEM: odaklanmak (-e odaklanır).' },
          { text: 'synthetic molecules', role: 'OBJECT', explanation_tr: 'NESNE: sentetik moleküller.' },
          { text: 'designed to', role: 'MODIFIER', explanation_tr: 'Kısaltılmış sıfat fiil (tasarlanmış olan).' },
          { text: 'inhibit', role: 'TARGET_WORD', explanation_tr: 'HEDEF FİİL: baskılamak, engellemek.', isTargetWord: true },
          { text: 'this pathological accumulation', role: 'OBJECT', explanation_tr: 'Mastar nesnesi: bu patolojik birikimi.' },
          { text: 'before irreversible neuronal loss occurs.', role: 'SUBORDINATE', explanation_tr: 'Zaman yan cümleciği (kalıcı kayıp olmadan önce).' }
        ],
        main_clause: {
          subject: 'recent pharmacological trials',
          verb: 'focus on',
          object: 'synthetic molecules'
        },
        subordinate_clause: {
          connector: 'before',
          clause: 'irreversible neuronal loss occurs',
          function_tr: 'Eylemin tamamlanması gereken kritik zaman sınırını çizen zarf yan cümleciği.'
        },
        interactive_question: {
          prompt: '"designed to inhibit" öbeği cümlede hangi kelimeyi nitelemektedir?',
          options: ['pharmacological trials', 'synthetic molecules', 'neuronal loss', 'consequence'],
          correct_index: 1,
          rationale_tr:
            '"designed to inhibit" niteleme grubu, hemen önündeki "synthetic molecules" (sentetik moleküller) ismini açıklar.'
        }
      }
    ],
    scaffold_questions: [
      {
        type: 'MAIN_IDEA',
        prompt: 'Paragrafın ana fikri aşağıdakilerden hangisidir?',
        options: [
          'Sinir sistemi hiçbir zaman toksik proteinlere karşı savunma geliştiremez.',
          'Yaşlanmayla ortaya çıkan toksik birikim ve bilişsel bozulmayı durdurmak için önleyici moleküler tedaviler araştırılmaktadır.',
          'Bilişsel fonksiyonlar birkaç hafta içinde tamamen geri döndürülebilir.',
          'Oksidatif stres sadece genç bireylerin sinir dokularında görülür.'
        ],
        correct_index: 1,
        explanation_tr:
          'Paragraf hem hastalığın mekanizmasını (savunmasızlık, birikim, bozulma) hem de buna karşı geliştirilen engelleme (inhibit) odaklı farmakolojik çözümü özetler.'
      },
      {
        type: 'INFERENCE',
        prompt: 'Metinden yola çıkarak farmakolojik denemelerle ilgili hangi çıkarım yapılabilir?',
        options: [
          'Tedavilerin nöron kaybı kalıcı hale gelmeden önce uygulanması kritik öneme sahiptir.',
          'Sentetik moleküller nöroplastisiteyi tamamen ortadan kaldırmaktadır.',
          'Denemeler yalnızca hayvan modelleri üzerinde yürütülmektedir.',
          'Araştırmacılar protein birikimini hiçbir zaman engelleyemeyeceklerini kabul etmiştir.'
        ],
        correct_index: 0,
        explanation_tr:
          '"before irreversible neuronal loss occurs" (kalıcı nöron kaybı gerçekleşmeden önce) ifadesi erken müdahalenin zorunlu olduğunu doğrular.'
      }
    ]
  },
  {
    id: 'reading-passage-2-energy',
    title: 'Güneş Pillerinde Silisyum ve Verimlilik Artışı',
    science_domain: 'physics',
    target_words: ['abundant', 'accelerate', 'enhance', 'negligible'],
    main_idea_tr:
      'Silisyumun yer kabuğunda bol bulunması güneş paneli üretimini sürdürülebilir kılarken, yeni katkılama teknikleri elektron transferini hızlandırmakta ve enerji kaybını ihmal edilebilir düzeye indirmektedir.',
    paragraph_text:
      'Because silicon is exceedingly abundant in the terrestrial crust, it has established itself as the dominant semiconductor for photovoltaic energy conversion. However, intrinsic silicon exhibits low carrier mobility at ambient temperatures. To overcome this limitation, solid-state physicists deliberately introduce dopants to accelerate electron transport. As a result of these microstructural modifications, energy dissipation becomes virtually negligible, which in turn enhances the overall thermodynamic efficiency of modern solar cells.',
    sentences: [
      {
        id: 's1-energy',
        sentence:
          'Because silicon is exceedingly abundant in the terrestrial crust, it has established itself as the dominant semiconductor for photovoltaic energy conversion.',
        translation_tr:
          'Silisyum yer kabuğunda son derece bol bulunduğu için, fotovoltayik enerji dönüşümünde baskın yarı iletken olarak yerini sağlamlaştırmıştır.',
        science_domain: 'physics',
        target_word_ids: ['abundant'],
        pedagogical_focus: 'CLAUSE_DECOMPOSITION',
        pedagogical_tip_tr:
          '"Because" neden-sonuç bağlacı silisyumun bol bulunmasını ana cümlenin gerekçesi yapar. Özne: "it" (silicon), Yüklem: "has established".',
        tokens: [
          { text: 'Because', role: 'CONNECTOR', explanation_tr: 'Neden-sonuç bağlacı (-dığı için). Gerekçeyi sunar.' },
          { text: 'silicon', role: 'SUBJECT', explanation_tr: 'Yan cümlenin öznesi: silisyum.' },
          { text: 'is', role: 'VERB', explanation_tr: 'Yan cümlenin yüklemi.' },
          { text: 'exceedingly', role: 'MODIFIER', explanation_tr: 'Zarf: aşırı derecede, fevkalade.' },
          { text: 'abundant', role: 'TARGET_WORD', explanation_tr: 'HEDEF KELİME: bol, zengin miktarda bulunan.', isTargetWord: true },
          { text: 'in the terrestrial crust,', role: 'MODIFIER', explanation_tr: 'Yer tamlayıcısı: yer kabuğunda.' },
          { text: 'it', role: 'SUBJECT', explanation_tr: 'ANA CÜMLENİN ÖZNESİ (silicon yerine).' },
          { text: 'has established', role: 'VERB', explanation_tr: 'ANA CÜMLENİN TEMEL FİİLİ (sağlamlaştırmıştır).' },
          { text: 'itself', role: 'OBJECT', explanation_tr: 'Dönüşlü zamir: kendisini.' },
          { text: 'as the dominant semiconductor for photovoltaic energy conversion.', role: 'MODIFIER', explanation_tr: 'Edat öbeği: baskın yarı iletken olarak.' }
        ],
        main_clause: {
          subject: 'it (silicon)',
          verb: 'has established',
          object: 'itself as the dominant semiconductor'
        },
        subordinate_clause: {
          connector: 'Because',
          clause: 'silicon is exceedingly abundant in the terrestrial crust',
          function_tr: 'Silisyumun tercih edilme gerekçesini sunan neden yan cümleciği.'
        },
        interactive_question: {
          prompt: 'Silisyumun baskın yarı iletken olmasının temel gerekçesi nedir?',
          options: ['Yüksek fiyatı', 'Yer kabuğunda bol bulunması', 'Düşük iletkenliği', 'Ağır bir metal olması'],
          correct_index: 1,
          rationale_tr:
            '"Because silicon is exceedingly abundant..." ifadesi açıkça bolluğun temel gerekçe olduğunu belirtir.'
        }
      },
      {
        id: 's2-energy',
        sentence:
          'To overcome this limitation, solid-state physicists deliberately introduce dopants to accelerate electron transport.',
        translation_tr:
          'Bu sınırlamanın üstesinden gelmek için katı hal fizikçileri elektron iletimini hızlandırmak amacıyla kasti olarak katkı maddeleri eklerler.',
        science_domain: 'physics',
        target_word_ids: ['accelerate'],
        pedagogical_focus: 'PASSIVE_VOICE_ANALYSIS',
        pedagogical_tip_tr:
          'Cümle amaç mastarı ("To overcome this limitation") ile başlar. Eyleyen: "solid-state physicists", Eylem: "introduce dopants", İkinci Amaç: "to accelerate electron transport".',
        tokens: [
          { text: 'To overcome this limitation,', role: 'MODIFIER', explanation_tr: 'Amaç bildiren mastar öbeği (üstesinden gelmek amacıyla).' },
          { text: 'solid-state physicists', role: 'SUBJECT', explanation_tr: 'ANA CÜMLENİN ÖZNESİ (katı hal fizikçileri).' },
          { text: 'deliberately', role: 'MODIFIER', explanation_tr: 'Zarf: bilerek, kasıtlı olarak.' },
          { text: 'introduce', role: 'VERB', explanation_tr: 'ANA CÜMLENİN TEMEL FİİLİ (dahil etmek, eklemek).' },
          { text: 'dopants', role: 'OBJECT', explanation_tr: 'NESNE: katkı atomları / maddeleri.' },
          { text: 'to', role: 'CONNECTOR', explanation_tr: 'Mastar eki: amaç bildirir (-mek için).' },
          { text: 'accelerate', role: 'TARGET_WORD', explanation_tr: 'HEDEF FİİL: hızlandırmak, ivme vermek.', isTargetWord: true },
          { text: 'electron transport.', role: 'OBJECT', explanation_tr: 'Amaç nesnesi: elektron iletimi.' }
        ],
        main_clause: {
          subject: 'solid-state physicists',
          verb: 'introduce',
          object: 'dopants'
        },
        interactive_question: {
          prompt: 'Fizikçilerin katkı maddeleri (dopants) eklemesinin amacı nedir?',
          options: ['Güneş pillerini ağırlaştırmak', 'Elektron iletimini hızlandırmak', 'Silisyumu eritmek', 'Maliyeti artırmak'],
          correct_index: 1,
          rationale_tr:
            '"to accelerate electron transport" ifadesi eylemin doğrudan amacını ifade eder.'
        }
      },
      {
        id: 's3-energy',
        sentence:
          'As a result of these microstructural modifications, energy dissipation becomes virtually negligible, which in turn enhances the overall thermodynamic efficiency of modern solar cells.',
        translation_tr:
          'Bu mikroyapısal değişikliklerin bir sonucu olarak, enerji kaybı neredeyse ihmal edilebilir hale gelir; bu da modern güneş hücrelerinin genel termodinamik verimliliğini artırır.',
        science_domain: 'physics',
        target_word_ids: ['negligible', 'enhance'],
        pedagogical_focus: 'RELATIVE_CLAUSE_UNPACKING',
        pedagogical_tip_tr:
          '", which in turn enhances..." yapısı önceki cümlenin tamamını niteleyen "non-defining relative clause" yapısıdır. Hangi durum verimliliği artırır? Enerji kaybının ihmal edilebilir düzeye inmesi.',
        tokens: [
          { text: 'As a result of these microstructural modifications,', role: 'CONNECTOR', explanation_tr: 'Neden-sonuç geçiş tümleci: bu değişikliklerin sonucu olarak.' },
          { text: 'energy dissipation', role: 'SUBJECT', explanation_tr: 'ÖZNE: enerji kaybı / dağılması.' },
          { text: 'becomes', role: 'VERB', explanation_tr: 'YÜKLEM: hale gelir.' },
          { text: 'virtually', role: 'MODIFIER', explanation_tr: 'Zarf: neredeyse, fiilen.' },
          { text: 'negligible,', role: 'TARGET_WORD', explanation_tr: 'HEDEF KELİME: ihmal edilebilir, önemsiz.', isTargetWord: true },
          { text: 'which in turn', role: 'CONNECTOR', explanation_tr: 'İlgi zamiri ve geçiş: bu durum da sırasıyla / karşılığında.' },
          { text: 'enhances', role: 'TARGET_WORD', explanation_tr: 'HEDEF FİİL: artırır, geliştirir.', isTargetWord: true },
          { text: 'the overall thermodynamic efficiency of modern solar cells.', role: 'OBJECT', explanation_tr: 'Nesne: modern güneş hücrelerinin genel verimliliği.' }
        ],
        main_clause: {
          subject: 'energy dissipation',
          verb: 'becomes',
          object: 'virtually negligible'
        },
        subordinate_clause: {
          connector: 'which',
          clause: 'in turn enhances the overall thermodynamic efficiency of modern solar cells',
          function_tr: 'Önceki tüm durumun yol açtığı verimlilik artışını açıklayan relative clause.'
        },
        interactive_question: {
          prompt: '"which" zamiri cümlede tam olarak neye gönderme yapmaktadır?',
          options: ['Sadece güneş hücrelerine', 'Sadece katkı maddelerine', 'Enerji kaybının neredeyse ihmal edilebilir hale gelmesine', 'Yer kabuğuna'],
          correct_index: 2,
          rationale_tr:
            'Virgülden sonra gelen ", which" tüm bir önceki cümleyi ("energy dissipation becomes virtually negligible") özetleyerek verimlilik artışının sebebi yapar.'
        }
      }
    ],
    scaffold_questions: [
      {
        type: 'DETAIL',
        prompt: 'Metne göre saf (intrinsic) silisyumun oda sıcaklığındaki temel sınırlaması nedir?',
        options: [
          'Düşük taşıyıcı hareketliliği göstermesi',
          'Yer kabuğunda bulunamaması',
          'Çok ağır olması',
          'Işığı hiç geçirmemesi'
        ],
        correct_index: 0,
        explanation_tr:
          '"intrinsic silicon exhibits low carrier mobility at ambient temperatures" cümlesi doğrudan bu sınırlamayı açıklar.'
      }
    ]
  }
];
