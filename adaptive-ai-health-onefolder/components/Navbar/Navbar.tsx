import Link from "next/link";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-clinic-border bg-white/70 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="group flex items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-clinic-blueSoft text-clinic-blue shadow-sm transition group-hover:scale-[1.02]">
            AI
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-slate-900">
              Adaptive AI Health
            </div>
            <div className="text-xs text-slate-500">Intelligence System</div>
          </div>
        </Link>

        <nav className="flex items-center gap-2 text-sm">
          <Link
            href="/"
            className="rounded-lg px-3 py-2 text-slate-600 transition hover:bg-clinic-blueSoft hover:text-slate-900"
          >
            Intake
          </Link>
          <Link
            href="/results"
            className="rounded-lg px-3 py-2 text-slate-600 transition hover:bg-clinic-blueSoft hover:text-slate-900"
          >
            Results
          </Link>
        </nav>
      </div>
    </header>
  );
}

