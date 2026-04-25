import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

export interface RuleHit {
  rule_id: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  old_snippet?: string;
  new_snippet?: string;
}

export interface RiskScore {
  semantic_score: number;
  rule_score: number;
  structural_score: number;
  combined: number;
  level: "critical" | "high" | "medium" | "low";
  drivers: string[];
}

export interface ClauseDiff {
  change_type: "added" | "removed" | "modified" | "unchanged";
  match_type: string;
  old_id?: string;
  new_id?: string;
  old_heading?: string;
  new_heading?: string;
  old_text?: string;
  new_text?: string;
  similarity?: number;
  risk: RiskScore;
  rule_hits: RuleHit[];
  summary: string;
}

export interface DiffResponse {
  total_clauses_old: number;
  total_clauses_new: number;
  added: number;
  removed: number;
  modified: number;
  unchanged: number;
  overall_risk: string;
  summary: string;
  diffs: ClauseDiff[];
}

export async function analyzeDiff(
  oldDocument: string,
  newDocument: string,
  threshold = 0.85
): Promise<DiffResponse> {
  const { data } = await api.post<DiffResponse>("/v1/diff", {
    old_document: oldDocument,
    new_document: newDocument,
    similarity_threshold: threshold,
  });
  return data;
}

export async function analyzeDiffFiles(
  oldFile: File,
  newFile: File,
  threshold = 0.85
): Promise<DiffResponse> {
  const form = new FormData();
  form.append("old_file", oldFile);
  form.append("new_file", newFile);
  form.append("similarity_threshold", String(threshold));
  const { data } = await api.post<DiffResponse>("/v1/diff/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
