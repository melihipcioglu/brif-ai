import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { INTERACTIVE_DECOMPOSITION_TASKS } from '../../../src/data/learning/interactiveDecompositionBank';
import { InteractiveDecomposerScreen } from '../../../src/components/learning/InteractiveDecomposerScreen';
import { createInitialLearnerProfile } from '../../../src/services/learning/dailyPlanner';
import type { LearnerProfile } from '../../../src/types/learning';

describe('Interactive Syntax Decomposition Workshop (I DO -> WE DO -> YOU DO)', () => {
  it('contains authentic tasks across all 3 scaffolding modes', () => {
    expect(INTERACTIVE_DECOMPOSITION_TASKS.length).toBe(3);

    const iDo = INTERACTIVE_DECOMPOSITION_TASKS.find((t) => t.mode === 'I_DO');
    const weDo = INTERACTIVE_DECOMPOSITION_TASKS.find((t) => t.mode === 'WE_DO');
    const youDo = INTERACTIVE_DECOMPOSITION_TASKS.find((t) => t.mode === 'YOU_DO');

    expect(iDo).toBeDefined();
    expect(weDo).toBeDefined();
    expect(youDo).toBeDefined();

    INTERACTIVE_DECOMPOSITION_TASKS.forEach((t) => {
      expect(t.tokens.length).toBeGreaterThan(4);
      expect(t.pedagogicalRationale.length).toBeGreaterThan(10);
      expect(Object.keys(t.tokenExplanations).length).toBeGreaterThan(0);
    });
  });

  it('renders interactive workbench, provides error pedagogy on wrong clicks, and advances through modes', () => {
    const profile = createInitialLearnerProfile();
    let updatedProfileResult: LearnerProfile | null = null;
    const handleFinish = (up: LearnerProfile) => {
      updatedProfileResult = up;
    };
    const handleCancel = vi.fn();

    render(
      <InteractiveDecomposerScreen
        profile={profile}
        onFinish={handleFinish}
        onCancel={handleCancel}
      />
    );

    // 1. I DO MODE
    expect(screen.getByText(/I DO: ÖĞRETMEN MODELİ/i)).toBeDefined();
    // Click any token in I DO mode (e.g. Although)
    const althoughToken = screen.getByText('Although');
    fireEvent.click(althoughToken);

    // Should show explanation and enable advance
    expect(screen.getByText(/Although zıtlık bağlacıdır/i)).toBeDefined();
    const nextBtn1 = screen.getByText(/Sonraki Aşamaya Geç →/i);
    fireEvent.click(nextBtn1);

    // 2. WE DO MODE
    expect(screen.getByText(/WE DO: BİRLİKTE ÇÖZÜMLEME/i)).toBeDefined();

    // Click WRONG trap token: "catalyze"
    const catalyzeToken = screen.getByText('catalyze');
    fireEvent.click(catalyzeToken);

    // Verify tailored pedagogical misconception feedback
    expect(screen.getByText(/TUZAK! "catalyze" bir fiildir fakat "that" sıfat cümleciğinin içindedir/i)).toBeDefined();

    // Click CORRECT token: "accelerate"
    const accelerateToken = screen.getByText('accelerate');
    fireEvent.click(accelerateToken);

    // Verify success feedback
    expect(screen.getByText(/DOĞRU! "accelerate" \(hızlandırır\) tüm cümlenin ana yüklemidir/i)).toBeDefined();
    const nextBtn2 = screen.getByText(/Sonraki Aşamaya Geç →/i);
    fireEvent.click(nextBtn2);

    // 3. YOU DO MODE
    expect(screen.getByText(/YOU DO: BAĞIMSIZ UYGULAMA/i)).toBeDefined();

    // Click CORRECT token: "melt"
    const meltToken = screen.getByText('melt');
    fireEvent.click(meltToken);

    expect(screen.getByText(/TEBRİKLER! "melt" \(erimek\) ana cümlenin temel yüklemidir/i)).toBeDefined();
    const finishBtn = screen.getByText(/Çözümleme Çalışmasını Tamamla →/i);
    fireEvent.click(finishBtn);

    expect(updatedProfileResult).not.toBeNull();
  });
});
