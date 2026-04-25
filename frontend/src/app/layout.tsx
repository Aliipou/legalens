import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LegaLens — Legal Document Intelligence",
  description: "Semantic diff engine for legal documents. Detect obligation shifts, liability changes, and 15+ high-risk legal patterns.",
  openGraph: {
    title: "LegaLens",
    description: "Legal reasoning and change intelligence engine",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50">
        <nav className="border-b border-slate-200 bg-white px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-slate-900">Lega<span className="text-blue-600">Lens</span></span>
            <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">v2.0</span>
          </div>
          <a href="/diff" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
            Analyze Document
          </a>
        </nav>
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
