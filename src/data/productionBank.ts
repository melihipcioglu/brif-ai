import { initialQuestions } from './initialQuestions';
import { batch1Questions } from './batch1';
import { batch2Questions } from './batch2';
import { batch3Questions } from './batch3';
import { batch4Questions } from './batch4';
import { batch5Questions } from './batch5';
import { batch6Questions } from './batch6';
import { batch7Questions } from './batch7';
import { batch8Questions } from './batch8';
import { batch9Questions } from './batch9';
import { batch10Questions } from './batch10';

export const phase9Bank = [
  ...initialQuestions,
  ...batch1Questions,
  ...batch2Questions,
  ...batch3Questions,
  ...batch4Questions,
  ...batch5Questions,
];

export const productionBank = [
  ...phase9Bank,
  ...batch6Questions,
  ...batch7Questions,
  ...batch8Questions,
  ...batch9Questions,
  ...batch10Questions,
];

