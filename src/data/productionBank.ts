import { initialQuestions } from './initialQuestions';
import { batch1Questions } from './batch1';
import { batch2Questions } from './batch2';
import { batch3Questions } from './batch3';
import { batch4Questions } from './batch4';
import { batch5Questions } from './batch5';

export const productionBank = [...initialQuestions, ...batch1Questions, ...batch2Questions, ...batch3Questions, ...batch4Questions, ...batch5Questions];
