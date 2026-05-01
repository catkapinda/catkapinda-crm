"use client";

import { useEffect, useMemo, useState } from "react";

type AuthSessionLoadingScreenProps = {
  title?: string;
  description?: string;
  note?: string;
};

type StepState = "pending" | "active" | "done";

const STEP_LABELS = [
  "Oturum doğrulanıyor",
  "Yetkiler kontrol ediliyor",
  "İlgili modül hazırlanıyor",
] as const;

function resolveStepState(progress: number, index: number): StepState {
  const thresholds = [26, 58, 84];
  if (progress >= thresholds[index]) {
    return "done";
  }
  if (index === 0) {
    return "active";
  }
  return progress >= thresholds[index - 1] ? "active" : "pending";
}

export function AuthSessionLoadingScreen({
  title = "Kontrol merkezi hazırlanıyor",
  description = "Yetki, oturum ve operasyon verileri güvenli şekilde hazırlanıyor.",
  note = "Birkaç saniye içinde yönlendirileceksiniz.",
}: AuthSessionLoadingScreenProps) {
  const [progress, setProgress] = useState(8);

  useEffect(() => {
    let frameId = 0;
    let mounted = true;
    const startedAt = performance.now();

    const tick = (now: number) => {
      if (!mounted) {
        return;
      }
      const elapsed = now - startedAt;
      const nextProgress = Math.min(90, 90 * (1 - Math.exp(-elapsed / 850)));
      setProgress((current) => (Math.abs(current - nextProgress) > 0.35 ? nextProgress : current));
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);
    return () => {
      mounted = false;
      window.cancelAnimationFrame(frameId);
    };
  }, []);

  const steps = useMemo(
    () =>
      STEP_LABELS.map((label, index) => ({
        label,
        state: resolveStepState(progress, index),
      })),
    [progress],
  );

  return (
    <div className="auth-session-screen" role="status" aria-live="polite" aria-busy="true">
      <div className="auth-session-network auth-session-network--left" aria-hidden="true" />
      <div className="auth-session-network auth-session-network--right" aria-hidden="true" />

      <div className="auth-session-shell">
        <div className="auth-session-wordmark">ÇAT KAPINDA</div>

        <section className="auth-session-card">
          <div className="auth-session-orb" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>

          <div className="auth-session-copy">
            <h2>{title}</h2>
            <p>{description}</p>
          </div>

          <div className="auth-session-divider" />

          <div className="auth-session-steps">
            {steps.map((step) => (
              <div key={step.label} className={`auth-session-step auth-session-step--${step.state}`}>
                <span className="auth-session-step-dot" aria-hidden="true" />
                <span className="auth-session-step-label">{step.label}</span>
                <span className="auth-session-step-state">
                  {step.state === "done" ? "Hazır" : step.state === "active" ? "Hazırlanıyor" : "Sırada"}
                </span>
              </div>
            ))}
          </div>

          <div className="auth-session-progress" aria-hidden="true">
            <div className="auth-session-progress-track">
              <div className="auth-session-progress-fill" style={{ width: `${progress}%` }}>
                <span className="auth-session-progress-shimmer" />
              </div>
            </div>
          </div>

          <div className="auth-session-note">{note}</div>
        </section>
      </div>

      <style jsx>{`
        .auth-session-screen {
          position: relative;
          min-height: 100vh;
          overflow: hidden;
          background:
            radial-gradient(circle at 50% 0%, rgba(247, 183, 49, 0.12), transparent 28%),
            radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.08), transparent 26%),
            radial-gradient(circle at 80% 26%, rgba(59, 130, 246, 0.06), transparent 24%),
            linear-gradient(180deg, #fffdfa 0%, #f8f6ef 100%);
          padding: 32px 20px;
          box-sizing: border-box;
          display: grid;
          place-items: center;
        }

        .auth-session-shell {
          position: relative;
          z-index: 1;
          width: min(620px, 100%);
          display: grid;
          gap: 22px;
          justify-items: center;
        }

        .auth-session-wordmark {
          color: #16356b;
          font-size: 0.9rem;
          font-weight: 800;
          letter-spacing: 0.34em;
          text-transform: uppercase;
          text-align: center;
          white-space: nowrap;
        }

        .auth-session-card {
          width: min(560px, 100%);
          padding: 28px 28px 24px;
          border-radius: 30px;
          background: rgba(255, 255, 255, 0.9);
          border: 1px solid rgba(214, 223, 238, 0.92);
          box-shadow: 0 28px 60px rgba(22, 42, 74, 0.08);
          display: grid;
          gap: 18px;
          justify-items: stretch;
        }

        .auth-session-orb {
          width: 74px;
          height: 74px;
          margin: 0 auto;
          border-radius: 999px;
          position: relative;
          background: radial-gradient(circle at 32% 30%, rgba(99, 150, 255, 0.16), rgba(99, 150, 255, 0.06));
          border: 1px solid rgba(99, 150, 255, 0.18);
          animation: orbitalPulse 1.8s ease-in-out infinite;
        }

        .auth-session-orb::after {
          content: "";
          position: absolute;
          inset: 10px;
          border-radius: 999px;
          border: 2px solid rgba(47, 91, 205, 0.22);
        }

        .auth-session-orb span {
          position: absolute;
          left: 50%;
          width: 24px;
          height: 4px;
          border-radius: 999px;
          background: linear-gradient(90deg, #1d48af, #4173eb);
          transform: translateX(-50%);
        }

        .auth-session-orb span:nth-child(1) {
          top: 24px;
        }

        .auth-session-orb span:nth-child(2) {
          top: 35px;
          width: 18px;
        }

        .auth-session-orb span:nth-child(3) {
          top: 46px;
          width: 22px;
        }

        .auth-session-copy {
          display: grid;
          gap: 8px;
          text-align: center;
        }

        .auth-session-copy h2 {
          margin: 0;
          color: #102b5d;
          font-size: clamp(1.9rem, 5vw, 2.45rem);
          line-height: 1.04;
          letter-spacing: -0.04em;
          font-weight: 800;
        }

        .auth-session-copy p {
          margin: 0;
          color: #60708c;
          font-size: 1rem;
          line-height: 1.65;
        }

        .auth-session-divider {
          height: 1px;
          background: linear-gradient(90deg, rgba(212, 221, 236, 0), rgba(212, 221, 236, 0.95), rgba(212, 221, 236, 0));
        }

        .auth-session-steps {
          display: grid;
          gap: 6px;
        }

        .auth-session-step {
          display: grid;
          grid-template-columns: 18px minmax(0, 1fr) auto;
          align-items: center;
          gap: 12px;
          padding: 12px 4px;
          border-bottom: 1px solid rgba(225, 231, 242, 0.8);
        }

        .auth-session-step:last-child {
          border-bottom: 0;
        }

        .auth-session-step-dot {
          width: 18px;
          height: 18px;
          border-radius: 999px;
          border: 1.5px solid rgba(154, 170, 198, 0.45);
          background: rgba(148, 163, 184, 0.12);
          position: relative;
        }

        .auth-session-step--active .auth-session-step-dot {
          border-color: rgba(45, 102, 225, 0.32);
          background: rgba(54, 110, 229, 0.18);
          animation: dotPulse 1.3s ease-in-out infinite;
        }

        .auth-session-step--done .auth-session-step-dot {
          border-color: rgba(30, 64, 175, 0.28);
          background: #1f4aa5;
        }

        .auth-session-step--done .auth-session-step-dot::after {
          content: "";
          position: absolute;
          left: 5px;
          top: 2px;
          width: 5px;
          height: 9px;
          border-right: 2px solid #ffffff;
          border-bottom: 2px solid #ffffff;
          transform: rotate(40deg);
        }

        .auth-session-step-label {
          min-width: 0;
          color: #10264d;
          font-size: 1rem;
          font-weight: 600;
          line-height: 1.35;
        }

        .auth-session-step-state {
          color: #789;
          font-size: 0.85rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .auth-session-step--active .auth-session-step-state,
        .auth-session-step--done .auth-session-step-state {
          color: #3d67cf;
        }

        .auth-session-step--done .auth-session-step-state {
          color: #18439a;
        }

        .auth-session-progress {
          padding-top: 4px;
        }

        .auth-session-progress-track {
          width: 100%;
          height: 10px;
          border-radius: 999px;
          overflow: hidden;
          background: rgba(88, 120, 180, 0.12);
          position: relative;
        }

        .auth-session-progress-fill {
          position: relative;
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #1b479f 0%, #3f7bff 55%, #74b7ff 100%);
          transition: width 180ms linear;
          overflow: hidden;
        }

        .auth-session-progress-shimmer {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.18) 45%,
            rgba(255, 255, 255, 0) 100%
          );
          animation: progressSweep 1.35s linear infinite;
        }

        .auth-session-note {
          text-align: center;
          color: #6f809b;
          font-size: 0.92rem;
          line-height: 1.5;
        }

        .auth-session-network {
          position: absolute;
          inset: auto;
          pointer-events: none;
          opacity: 0.5;
          filter: saturate(0.9);
        }

        .auth-session-network::before,
        .auth-session-network::after {
          content: "";
          position: absolute;
          border-radius: 999px;
          background: rgba(77, 143, 255, 0.16);
          box-shadow: 0 0 0 8px rgba(77, 143, 255, 0.06);
        }

        .auth-session-network--left {
          left: -40px;
          top: 18%;
          width: 260px;
          height: 240px;
          background:
            radial-gradient(circle at 24% 28%, rgba(77, 143, 255, 0.18) 0 6px, transparent 7px),
            radial-gradient(circle at 74% 54%, rgba(77, 143, 255, 0.22) 0 7px, transparent 8px),
            radial-gradient(circle at 38% 88%, rgba(77, 143, 255, 0.18) 0 6px, transparent 7px),
            linear-gradient(120deg, transparent 0 28%, rgba(128, 160, 219, 0.18) 28% 29%, transparent 29% 100%),
            linear-gradient(65deg, transparent 0 55%, rgba(128, 160, 219, 0.16) 55% 56%, transparent 56% 100%);
        }

        .auth-session-network--right {
          right: -24px;
          top: 24%;
          width: 280px;
          height: 260px;
          background:
            radial-gradient(circle at 78% 22%, rgba(77, 143, 255, 0.2) 0 6px, transparent 7px),
            radial-gradient(circle at 42% 56%, rgba(77, 143, 255, 0.24) 0 7px, transparent 8px),
            radial-gradient(circle at 70% 88%, rgba(77, 143, 255, 0.18) 0 6px, transparent 7px),
            linear-gradient(115deg, transparent 0 44%, rgba(128, 160, 219, 0.18) 44% 45%, transparent 45% 100%),
            linear-gradient(58deg, transparent 0 52%, rgba(128, 160, 219, 0.16) 52% 53%, transparent 53% 100%);
        }

        @keyframes dotPulse {
          0%,
          100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.08);
            opacity: 0.84;
          }
        }

        @keyframes progressSweep {
          0% {
            transform: translateX(-120%);
          }
          100% {
            transform: translateX(120%);
          }
        }

        @keyframes orbitalPulse {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.02);
          }
        }

        @media (max-width: 640px) {
          .auth-session-screen {
            padding: 24px 16px;
          }

          .auth-session-card {
            padding: 24px 18px 20px;
          }

          .auth-session-copy h2 {
            font-size: 1.9rem;
          }

          .auth-session-copy p {
            font-size: 0.94rem;
          }

          .auth-session-step {
            grid-template-columns: 18px minmax(0, 1fr);
          }

          .auth-session-step-state {
            grid-column: 2;
            font-size: 0.8rem;
          }

          .auth-session-network {
            opacity: 0.32;
          }
        }
      `}</style>
    </div>
  );
}
