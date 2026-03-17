# Adaptive AI Health Intelligence System (Frontend)

Modern, clinical, responsive Next.js + Tailwind frontend with:
- Multi-step intake form (validated, progress bar)
- Result cards (sorted by confidence)
- Detailed modal view (collapsible sections)
- Loading skeletons
- Mandatory trust elements (disclaimer + confidence explanation)
- "Download Health Summary" PDF generation

## Prerequisites
- Node.js 20+ and npm

## Run locally
```bash
cd adaptive-ai-health
npm install
npm run dev
```

Open `http://localhost:3000`.

## API routes (local mocks)
- `POST /api/intake`
- `POST /api/predict`
- `POST /api/report/generate` (returns a PDF)

