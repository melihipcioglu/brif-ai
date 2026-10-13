import React from 'react';
import { createRoot } from 'react-dom/client';
import { ExamApp } from './components/exam/ExamApp';
import { registerServiceWorker } from './pwa';

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <ExamApp />
    </React.StrictMode>
  );
}

registerServiceWorker();
