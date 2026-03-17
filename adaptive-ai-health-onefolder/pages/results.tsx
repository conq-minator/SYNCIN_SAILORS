import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar/Navbar";
import { ResultCardGrid } from "@/components/Cards/ResultCardGrid";
import { Modal } from "@/components/Modal/Modal";
import { CollapsibleSection } from "@/components/Modal/CollapsibleSection";
import { postGenerateReport } from "@/lib/api";
import { clearSession, loadSession } from "@/lib/storage";
import type { PredictionCard } from "@/lib/types";

export default function ResultsPage() {
  const [selected, setSelected] = useState<PredictionCard | null>(null);
  const [session, setSession] = useState<ReturnType<typeof loadSession>>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    setSession(loadSession());
  }, []);

  const cards = useMemo(() => {
    const list = session?.result.predictions ?? [];
    return [...list].sort((a, b) => b.confidence - a.confidence);
  }, [session]);

  async function onDownloadPdf() {
    if (!session) return;
    setReportError(null);
    setReportBusy(true);
    try {
      const blob = await postGenerateReport({
        intake: session.intake,
        predictions: session.result.predictions
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "health-summary.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setReportError(e instanceof Error ? e.message : "Failed to download report");
    } finally {
      setReportBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="mx-auto w-full max-w-6xl px-4 py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Results</h1>
            <p className="mt-1 text-sm text-slate-600">
              Cards are sorted by highest confidence first.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onDownloadPdf}
              disabled={!session || reportBusy}
              className="rounded-xl bg-clinic-blue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {reportBusy ? "Generating..." : "Download Health Summary"}
            </button>
            <button
              onClick={() => {
                clearSession();
                setSession(null);
              }}
              className="rounded-xl border border-clinic-border bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <section className="lg:col-span-4">
            <div className="space-y-3">
              <TrustDisclaimer />
              <ConfidenceExplanation />

              {reportError ? (
                <div className="rounded-xl border border-red-200 bg-clinic-redSoft px-4 py-3 text-sm font-medium text-red-800">
                  {reportError}
                </div>
              ) : null}

              {!session ? (
                <div className="rounded-2xl border border-clinic-border bg-white p-5 shadow-card">
                  <div className="text-sm font-semibold text-slate-900">
                    No results yet
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    Complete the intake form to generate predictions.
                  </div>
                  <Link
                    href="/"
                    className="mt-4 inline-flex rounded-xl bg-clinic-green px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-95"
                  >
                    Start intake
                  </Link>
                </div>
              ) : (
                <div className="rounded-2xl border border-clinic-border bg-white p-5 shadow-card">
                  <div className="text-xs font-semibold text-slate-700">
                    Patient summary (provided)
                  </div>
                  <div className="mt-2 text-sm text-slate-900">
                    {session.intake.personalInfo.fullName || "—"}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    DOB: {session.intake.personalInfo.dob || "—"} • Gender:{" "}
                    {session.intake.personalInfo.gender}
                  </div>
                  <div className="mt-3 text-xs text-slate-500">
                    Symptoms: {session.intake.symptoms.length}
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="lg:col-span-8">
            {session ? (
              <ResultCardGrid cards={cards} onSelect={setSelected} />
            ) : (
              <div className="rounded-2xl border border-clinic-border bg-white p-6 shadow-card">
                <div className="h-3 w-1/2 animate-pulse rounded-full bg-slate-100" />
                <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <SkeletonCard />
                  <SkeletonCard />
                  <SkeletonCard />
                  <SkeletonCard />
                </div>
              </div>
            )}
          </section>
        </div>

        <Modal
          open={!!selected}
          title={selected ? selected.diseaseName : "Details"}
          onClose={() => setSelected(null)}
        >
          {selected ? <DetailsBody card={selected} /> : null}
        </Modal>
      </main>
    </div>
  );
}

function TrustDisclaimer() {
  return (
    <div className="rounded-xl border border-clinic-border bg-clinic-blueSoft px-4 py-3">
      <div className="text-xs font-semibold text-slate-900">Disclaimer</div>
      <div className="mt-1 text-sm text-slate-700">
        This system provides assistive insights and does not replace medical
        diagnosis.
      </div>
    </div>
  );
}

function ConfidenceExplanation() {
  return (
    <div className="rounded-xl border border-clinic-border bg-white px-4 py-3">
      <div className="text-xs font-semibold text-slate-900">
        Confidence explanation
      </div>
      <div className="mt-1 text-sm text-slate-700">
        Confidence reflects pattern matching with known data.
      </div>
    </div>
  );
}

function DetailsBody({ card }: { card: PredictionCard }) {
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-clinic-border bg-white px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs font-semibold text-slate-700">Confidence</div>
          <div className="text-sm font-semibold text-slate-900">
            {Math.round(card.confidence)}%
          </div>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-clinic-blue transition-[width] duration-500"
            style={{ width: `${Math.max(0, Math.min(100, card.confidence))}%` }}
          />
        </div>
      </div>

      <CollapsibleSection title="Symptoms matched" defaultOpen>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {card.details.symptomsMatched.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </CollapsibleSection>

      <CollapsibleSection title="Supporting factors (vitals, history)" defaultOpen>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {card.details.supportingFactors.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </CollapsibleSection>

      <CollapsibleSection title="Contradictions" defaultOpen={false}>
        {card.details.contradictions.length ? (
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {card.details.contradictions.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <div className="text-sm text-slate-600">None detected.</div>
        )}
      </CollapsibleSection>

      <CollapsibleSection title="Confidence reasoning" defaultOpen>
        <div className="text-sm text-slate-700">{card.details.confidenceReasoning}</div>
      </CollapsibleSection>

      <CollapsibleSection title="Guidance" defaultOpen>
        <div className="text-sm text-slate-700">{card.details.guidance}</div>
      </CollapsibleSection>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-clinic-border bg-white p-5 shadow-card">
      <div className="h-3 w-2/3 animate-pulse rounded-full bg-slate-100" />
      <div className="mt-3 h-3 w-full animate-pulse rounded-full bg-slate-100" />
      <div className="mt-2 h-3 w-5/6 animate-pulse rounded-full bg-slate-100" />
      <div className="mt-6 h-2 w-full animate-pulse rounded-full bg-slate-100" />
    </div>
  );
}

