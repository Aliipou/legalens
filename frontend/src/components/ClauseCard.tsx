"use client";
import { useState } from "react";
import { clsx } from "clsx";
import type { ClauseDiff } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";

const borderColors = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-amber-500",
  low: "border-l-green-500",
};

const changeBg = {
  added: "bg-green-50",
  removed: "bg-red-50",
  modified: "bg-amber-50",
  unchanged: "bg-white",
};

export function ClauseCard({ diff, index }: { diff: ClauseDiff; index: number }) {
  const [expanded, setExpanded] = useState(diff.change_type !== "unchanged");
  const borderColor = borderColors[diff.risk.level as keyof typeof borderColors] ?? "border-l-slate-300";
  const bg = changeBg[diff.change_type] ?? "bg-white";

  return (
    <div className={clsx("rounded-lg border border-slate-200 border-l-4 shadow-sm overflow-hidden", borderColor, bg)}>
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-black/5 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xs font-mono text-slate-400 shrink-0">#{index + 1}</span>
          <span className={clsx("shrink-0 text-xs font-semibold uppercase px-2 py-0.5 rounded",
            diff.change_type === "added" && "bg-green-200 text-green-800",
            diff.change_type === "removed" && "bg-red-200 text-red-800",
            diff.change_type === "modified" && "bg-amber-200 text-amber-800",
            diff.change_type === "unchanged" && "bg-slate-200 text-slate-600",
          )}>
            {diff.change_type}
          </span>
          <span className="truncate text-sm text-slate-700">
            {diff.old_heading ?? diff.new_heading ?? diff.summary}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-4 shrink-0">
          <RiskBadge level={diff.risk.level} />
          {diff.similarity != null && (
            <span className="text-xs text-slate-400">sim={diff.similarity.toFixed(2)}</span>
          )}
          <span className="text-slate-400">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 px-4 py-4 space-y-4">
          {/* Text comparison */}
          {(diff.old_text || diff.new_text) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {diff.old_text && (
                <div>
                  <div className="mb-1 text-xs font-semibold text-slate-500 uppercase">Before</div>
                  <div className="rounded bg-red-50 border border-red-100 p-3 text-sm text-slate-700 whitespace-pre-wrap font-mono">
                    {diff.old_text}
                  </div>
                </div>
              )}
              {diff.new_text && (
                <div>
                  <div className="mb-1 text-xs font-semibold text-slate-500 uppercase">After</div>
                  <div className="rounded bg-green-50 border border-green-100 p-3 text-sm text-slate-700 whitespace-pre-wrap font-mono">
                    {diff.new_text}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Risk breakdown */}
          <div className="rounded-lg bg-white border border-slate-200 p-3 space-y-2">
            <div className="text-xs font-semibold text-slate-500 uppercase">Risk Breakdown</div>
            <div className="flex gap-4 text-sm">
              <span>Semantic: <b>{diff.risk.semantic_score.toFixed(0)}</b></span>
              <span>Rules: <b>{diff.risk.rule_score}</b></span>
              <span>Structural: <b>{diff.risk.structural_score}</b></span>
              <span>Combined: <b>{diff.risk.combined.toFixed(0)}</b></span>
            </div>
          </div>

          {/* Drivers */}
          {diff.risk.drivers.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-semibold text-slate-500 uppercase">Risk Drivers</div>
              <ul className="space-y-1">
                {diff.risk.drivers.map((d, i) => (
                  <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                    <span className="mt-0.5 text-amber-500">•</span>{d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rule hits */}
          {diff.rule_hits.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-semibold text-slate-500 uppercase">Rule Hits ({diff.rule_hits.length})</div>
              <div className="space-y-1">
                {diff.rule_hits.map((h) => (
                  <div key={h.rule_id} className="text-xs rounded border border-slate-100 bg-slate-50 px-3 py-2 flex items-start gap-2">
                    <RiskBadge level={h.severity} />
                    <span className="text-slate-700">{h.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
