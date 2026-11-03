# LLM Knowledge Pipeline 2.0 — React SaaS Frontend

A modern, enterprise-grade AI SaaS application built with **React 19**, **Vite**, **TypeScript**, **Tailwind CSS**, and **Framer Motion**, powered by **FastAPI** and **Sarvam AI**.

---

## 🎨 Technology Stack

- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4 (Glassmorphic dark design system)
- **Routing**: React Router DOM v7 (Multi-page client-side SPA)
- **HTTP Client**: Axios with centralized error handling & timeout resilience
- **Icons**: Lucide React
- **Animations**: Framer Motion (Page transitions, floating toast alerts)
- **Analytics & Charts**: Recharts (Volume distribution & quality scoring)

---

## 🧭 Application Pages

| Route | Page | Purpose |
| :--- | :--- | :--- |
| `/dashboard` | **Dashboard** | Metric counters, Recharts volume distribution, system diagnostics, and recent documents library. |
| `/ingestion` | **Document Ingestion** | Drag-and-drop upload (PDF, DOCX, TXT), boundary-aware chunk preview (0 LLM credits), and Sarvam Map-Reduce synthesis. |
| `/knowledge` | **Knowledge Explorer** | Executive synthesis copy, structured fact & entity catalog, and synthetic instruction-tuning Q&A pairs. |
| `/chunks` | **Chunks Inspector** | Boundary-aware segmented chunks with token estimations, page citations, search filter, and pagination. |
| `/quality` | **Quality & Evaluation** | Overall health score, citation grounding audit, Jaccard redundancy benchmarking, and duplicate pair diffs. |
| `/search` | **AI Knowledge Search** | Conversational RAG interface with live vector search and grounded Sarvam AI answers. |
| `/exports` | **Export Center** | Multi-format downloads for Hugging Face `.jsonl`, vector `.json`, tabular `.csv`, and brief `.md`. |
| `/documents` | **Document Library** | Persistent SQLite document management, 1-click reopen, and modal confirmation delete. |
| `/settings` | **Settings** | Sarvam AI model diagnostics, SQLite WAL engine parameters, and UI preferences. |

---

## 🚀 Running the Frontend

### 1. Development Mode
```bash
cd frontend
npm run dev
```
Opens at **`http://localhost:5173`** with hot module replacement and automatic API proxying to `http://127.0.0.1:8000`.

### 2. Production Build
```bash
cd frontend
npm run build
```
Generates optimized static assets in `frontend/dist/`.

---

## 📁 Frontend Directory Structure

```
frontend/
├── src/
│   ├── types/               # TypeScript interfaces matching FastAPI schemas
│   ├── services/            # Axios API client & error formatters
│   ├── contexts/            # DocumentContext & ToastContext providers
│   ├── components/
│   │   ├── layout/          # Sidebar, Header, and MainLayout
│   │   └── common/          # MetricCard, EmptyState, ConfirmModal, LoadingSkeleton
│   ├── pages/               # 9 dedicated page components
│   ├── App.tsx              # React Router DOM routing tree
│   ├── main.tsx             # Application entrypoint
│   └── index.css            # Dark glassmorphic design system
├── public/                  # Static assets
├── vite.config.ts           # Vite + Tailwind + Proxy configuration
└── tsconfig.json            # Strict TypeScript configuration
```
