"use client";
import { useState, useRef } from "react";
import { analyzeDiff, analyzeDiffFiles, type DiffResponse } from "@/lib/api";
import { ClauseCard } from "@/components/ClauseCard";
import { RiskBadge } from "@/components/RiskBadge";

const SAMPLE_OLD = `1. Payment Terms
Party A shall pay all invoices within 30 days of receipt.

2. Limitation of Liability
Company shall not be liable for any indirect, consequential, or punitive damages.

3. Governing Law
This agreement shall be governed by and construed in accordance with Finnish law.

4. Termination
Either party may terminate this agreement with 90 days written notice.`;

const SAMPLE_NEW = `1. Payment Terms
Party A may pay all invoices within 90 days of receipt. Late payment incurs a 5% monthly penalty.

2. Governing Law
This agreement shall be governed by Swedish law. All disputes shall be submitted to binding arbitration under ICC rules.

3. Termination
Either party may terminate this agreement with 14 days written notice. Party A hereby waives any right to claim damages upon termination.

4. Indemnification
Party A shall indemnify and hold harmless Company against all claims, losses, and damages arising from Party A's use of the services.`;

type Tab = "text" | "file";

export default function DiffPage() {
  const [tab, setTab] = useState<Tab>("text");
  const [oldDoc, setOldDoc] = useState(SAMPLE_OLD);
  const [newDoc, setNewDoc] = useState(SAMPLE_NEW);
  const [oldFile, setOldFile] = useState<File | null>(null);
  const [newFile, setNewFile] = useState<File | null>(null);
  const [threshold, setThreshold] = useState(0.85);
  const [result, setResult] = useState<DiffResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const filterLevel = useState<string>("all");
  const [activeFilter, setActiveFilter] = filterLevel;

  async function handleAnalyze() {
    setError(null);
    setLoading(true);
    try {
      let data: DiffResponse;
      if (tab === "file" && oldFile && newFile) {
        data = await analyzeDiffFiles(oldFile, newFile, threshold);
      } else {
        data = await analyzeDiff(oldDoc, newDoc, threshold);
      }
      setResult(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const filteredDiffs = result?.diffs.filter((d) => {
    if (activeFilter === "all") return true;
    if (activeFilter === "changed") return d.change_type !== "unchanged";
    return d.risk.level === activeFilter || d.change_type === activeFilter;
  }) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Document Analysis</h1>
        <p className="mt-1 text-slate-500">Paste two versions of a legal document to detect changes and risk.</p>
      </div>

      {/* Input panel */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-200">
          {(["text", "file"] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${tab === t ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
              {t === "text" ? "Paste Text" : "Upload Files"}
            </button>
          ))}
        </div>

        {tab === "text" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Original Document</label>
              <textarea value={oldDoc} onChange={(e) => setOldDoc(e.target.value)}
                className="w-full h-56 rounded-lg border border-slate-300 p-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Paste original contract text…" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Revised Document</label>
              <textarea value={newDoc} onChange={(e) => setNewDoc(e.target.value)}
                className="w-full h-56 rounded-lg border border-slate-300 p-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Paste revised contract text…" />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[["Original", setOldFile], ["Revised", setNewFile]].map(([label, setter]) => (
              <div key={label as string}>
                <label className="block text-sm font-medium text-slate-700 mb-1">{label as string} File (.txt, .md)</label>
                <input type="file" accept=".txt,.md"
                  onChange={(e) => (setter as typeof setOldFile)(e.target.files?.[0] ?? null)}
                  className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
              </div>
            ))}
          </div>
        )}

        {/* Settings */}
        <div className="flex items-center gap-4">
          <label className="text-sm text-slate-600">Similarity threshold:</label>
          <input type="range" min={0.5} max={0.99} step={0.01} value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-32" />
          <span className="text-sm font-mono text-slate-700">{threshold.toFixed(2)}</span>
        </div>

        {error && <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>}

        <button onClick={handleAnalyze} disabled={loading}
          className="w-full rounded-xl bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
          {loading ? "Analyzing…" : "Analyze →"}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div ref={resultRef} className="space-y-6">
          {/* Summary bar */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Analysis Result</h2>
                <p className="mt-1 text-sm text-slate-500">{result.summary}</p>
              </div>
              <RiskBadge level={result.overall_risk} />
            </div>
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                ["Added", result.added, "text-green-700"],
                ["Removed", result.removed, "text-red-700"],
                ["Modified", result.modified, "text-amber-700"],
                ["Unchanged", result.unchanged, "text-slate-600"],
              ].map(([label, val, cls]) => (
                <div key={label as string} className="rounded-lg bg-slate-50 p-3 text-center">
                  <div className={`text-2xl font-bold ${cls}`}>{val as number}</div>
                  <div className="text-xs text-slate-500">{label as string}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Filter bar */}
          <div className="flex gap-2 flex-wrap">
            {["all", "changed", "critical", "high", "medium", "low"].map((f) => (
              <button key={f} onClick={() => setActiveFilter(f)}
                className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${activeFilter === f ? "bg-blue-600 text-white" : "bg-white border border-slate-300 text-slate-600 hover:bg-slate-50"}`}>
                {f}
              </button>
            ))}
          </div>

          {/* Clause cards */}
          <div className="space-y-3">
            {filteredDiffs.length === 0
              ? <div className="text-center text-slate-400 py-8">No clauses match this filter.</div>
              : filteredDiffs.map((d, i) => <ClauseCard key={i} diff={d} index={i} />)
            }
          </div>
        </div>
      )}
    </div>
  );
}
