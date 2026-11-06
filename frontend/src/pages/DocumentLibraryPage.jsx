import React from "react";
import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";

export default function DocumentLibraryPage() {
  return (
    <div className="max-w-4xl mx-auto animate-slideUp">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Document Library</h1>
        <p className="text-slate-400 mt-1">Upload PDFs and research papers for document-based research</p>
      </div>
      <div className="glass-card p-12 flex flex-col items-center gap-4 text-center border-2 border-dashed border-white/10">
        <div className="w-16 h-16 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center justify-center">
          <BookOpen size={28} className="text-amber-400" />
        </div>
        <h2 className="text-xl font-semibold text-slate-300">Document upload coming soon</h2>
        <p className="text-slate-500 max-w-sm">
          RAG (Retrieval Augmented Generation) with PDF and document support will be available in Phase 5.
        </p>
        <p className="text-xs text-slate-600">Powered by Qdrant + HuggingFace sentence-transformers</p>
      </div>
    </div>
  );
}
