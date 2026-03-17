import { Navbar } from "@/components/Navbar/Navbar";
import { IntakeWizard } from "@/components/Form/IntakeWizard";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="mx-auto w-full max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <section className="lg:col-span-5">
            <div className="rounded-2xl border border-clinic-border bg-white p-6 shadow-card">
              <div className="inline-flex items-center gap-2 rounded-full bg-clinic-greenSoft px-3 py-1 text-xs font-semibold text-clinic-green">
                Clinical • Minimal • Private
              </div>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">
                Adaptive AI Health Intelligence System
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Share symptoms, vitals, and history to generate assistive insights.
                Results are presented as confidence-ranked cards with clear rationale.
              </p>

              <div className="mt-6 space-y-3">
                <TrustDisclaimer />
                <ConfidenceExplanation />
              </div>
            </div>
          </section>

          <section className="lg:col-span-7">
            <IntakeWizard />
          </section>
        </div>
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

