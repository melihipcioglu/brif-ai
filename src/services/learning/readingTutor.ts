import type {
  ReadingStrategyTopic,
  ScaffoldLevel,
  AcademicReadingPassage,
  LearnerProfile
} from '../../types/learning';
import { academicReadingBank } from '../../data/learning/academicReadingBank';

export function getRecommendedScaffoldLevel(
  topic: ReadingStrategyTopic,
  profile?: LearnerProfile
): ScaffoldLevel {
  if (!profile) return 'SYSTEM_MODEL';
  const stats = profile.readingMastery[topic];
  if (!stats || stats.encounters < 2) return 'SYSTEM_MODEL';
  if (stats.accuracy >= 0.8 && stats.encounters >= 4) return 'INDEPENDENT';
  return 'GUIDED_PROMPT';
}

export function findPassageForSkill(topic: ReadingStrategyTopic): AcademicReadingPassage {
  const match = academicReadingBank.find((p) =>
    p.sentences.some((s) => s.pedagogical_focus === topic)
  );
  return match ?? academicReadingBank[0]!;
}

export function evaluateReadingResponse(
  passage: AcademicReadingPassage,
  questionIndex: number,
  selectedIndex: number
): {
  readonly isCorrect: boolean;
  readonly explanation_tr: string;
} {
  const q = passage.scaffold_questions[questionIndex];
  if (!q) {
    return { isCorrect: false, explanation_tr: 'Soru bulunamadı.' };
  }
  const isCorrect = selectedIndex === q.correct_index;
  return {
    isCorrect,
    explanation_tr: q.explanation_tr
  };
}

export function evaluateSentenceInteractiveQuestion(
  passage: AcademicReadingPassage,
  sentenceIndex: number,
  selectedIndex: number
): {
  readonly isCorrect: boolean;
  readonly explanation_tr: string;
} {
  const sentence = passage.sentences[sentenceIndex];
  if (!sentence || !sentence.interactive_question) {
    return { isCorrect: false, explanation_tr: 'Alıştırma bulunamadı.' };
  }
  const q = sentence.interactive_question;
  const isCorrect = selectedIndex === q.correct_index;
  return {
    isCorrect,
    explanation_tr: q.rationale_tr
  };
}
