import Link from "next/link";

const RULES = [
  { icon: "⚠️", title: "Obligation Shift", desc: "shall → may: mandatory obligation weakened to discretionary" },
  { icon: "🛡️", title: "Liability Changes", desc: "Liability shields added, removed, or altered" },
  { icon: "💰", title: "Penalty & Damages", desc: "Financial amounts, percentages, and liquidated damages" },
  { icon: "📅", title: "Deadline Changes", desc: "Time constraints extended, shortened, or removed" },
  { icon: "⚖️", title: "Arbitration", desc: "Dispute resolution clauses and jurisdiction changes" },
  { icon: "🔒", title: "Irrevocability", desc: "Perpetual, irrevocable, or exclusive scope changes" },
  { icon: "✍️", title: "Waiver & Indemnity", desc: "Rights waived or indemnification obligations added" },
  { icon: "🚪", title: "Termination", desc: "Exit rights added, removed, or conditions changed" },
];

export default function HomePage() {
  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="text-center pt-8 space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-sm text-blue-700">
          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          Legal reasoning engine — not just a diff tool
        </div>
        <h1 className="text-5xl font-bold text-slate-900 leading-tight">
          Understand what changed in your<br />
          <span className="text-blue-600">legal documents</span>
        </h1>
        <p className="max-w-2xl mx-auto text-lg text-slate-600">
          LegaLens uses semantic embeddings + legal rule engine to detect obligation shifts,
          liability changes, arbitration clauses, and 15+ other high-risk patterns — with
          clause-level risk scoring and full explainability.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/diff" className="rounded-xl bg-blue-600 px-8 py-3 text-base font-semibold text-white hover:bg-blue-700 shadow-sm transition-colors">
            Analyze Documents →
          </Link>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
            className="rounded-xl border border-slate-300 bg-white px-8 py-3 text-base font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
            API Docs
          </a>
        </div>
      </section>

      {/* Risk rules grid */}
      <section>
        <h2 className="text-center text-2xl font-bold text-slate-900 mb-8">Detected Risk Patterns</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {RULES.map((r) => (
            <div key={r.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
              <div className="text-2xl mb-2">{r.icon}</div>
              <div className="font-semibold text-slate-900">{r.title}</div>
              <div className="mt-1 text-sm text-slate-500">{r.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-xl font-bold text-slate-900 mb-6">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            ["1. Segment", "Splits document into hierarchical clauses: sections, (a)(b) subclauses, bullets"],
            ["2. Match", "ID-first matching by section number, semantic fallback via embeddings"],
            ["3. Rule Engine", "15+ legal rules fire on each modified clause pair"],
            ["4. Score", "Hybrid model: semantic 30% + rules 55% + structural 15% → risk level"],
          ].map(([step, desc]) => (
            <div key={step} className="space-y-2">
              <div className="font-bold text-blue-600">{step}</div>
              <div className="text-sm text-slate-600">{desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
