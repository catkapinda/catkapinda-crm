import type { CSSProperties } from "react";

type FieldDensity = "compact" | "roomy";
type PillDensity = "compact" | "regular";
type PillTone = "accent" | "soft" | "muted" | "warn" | "ink";
type FeedbackTone = "info" | "error" | "success";

type FieldStyleOptions = {
  density?: FieldDensity;
  backgroundAlpha?: number;
  fontSize?: CSSProperties["fontSize"];
  outline?: CSSProperties["outline"];
};

export function managementFieldStyle(options: FieldStyleOptions = {}): CSSProperties {
  const {
    density = "compact",
    backgroundAlpha = density === "roomy" ? 0.92 : 0.9,
    fontSize = density === "compact" ? "0.92rem" : undefined,
    outline,
  } = options;
  const layout =
    density === "roomy"
      ? { padding: "13px 14px", borderRadius: "16px" }
      : { padding: "10px 12px", borderRadius: "12px" };

  return {
    width: "100%",
    padding: layout.padding,
    borderRadius: layout.borderRadius,
    border: "1px solid var(--line)",
    background: `rgba(255, 255, 255, ${backgroundAlpha})`,
    color: "var(--text)",
    font: "inherit",
    ...(fontSize ? { fontSize } : {}),
    ...(outline !== undefined ? { outline } : {}),
  };
}

export function managementPillStyle(
  tone: PillTone,
  density: PillDensity = "compact",
): CSSProperties {
  const palette =
    tone === "accent"
      ? {
          background: "rgba(15, 95, 215, 0.1)",
          color: "#0f5fd7",
          border: "1px solid rgba(15, 95, 215, 0.14)",
        }
      : tone === "warn"
        ? {
            background: "rgba(230, 140, 55, 0.12)",
            color: "#b96a18",
            border: "1px solid rgba(230, 140, 55, 0.16)",
          }
        : tone === "ink"
          ? {
              background: "rgba(27, 42, 63, 0.12)",
              color: "#1b2a3f",
              border: "1px solid rgba(27, 42, 63, 0.12)",
            }
          : {
              background: "rgba(95, 118, 152, 0.1)",
              color: "#5f7698",
              border: "1px solid rgba(95, 118, 152, 0.12)",
            };
  const size =
    density === "regular"
      ? { padding: "6px 10px", fontSize: "0.76rem" }
      : { padding: "4px 8px", fontSize: "0.68rem" };

  return {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: "999px",
    fontWeight: 800,
    ...size,
    ...palette,
  };
}

export const neutralOutlineButtonStyle: CSSProperties = {
  borderRadius: "16px",
  padding: "13px 14px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  fontWeight: 800,
  fontSize: "0.92rem",
  cursor: "pointer",
};

export function dangerOutlineButtonStyle(disabled: boolean): CSSProperties {
  return {
    borderRadius: "16px",
    padding: "13px 14px",
    border: "1px solid rgba(205, 70, 66, 0.18)",
    background: disabled ? "rgba(205, 70, 66, 0.04)" : "rgba(205, 70, 66, 0.08)",
    color: disabled ? "rgba(181, 54, 50, 0.5)" : "#b53632",
    fontWeight: 800,
    fontSize: "0.92rem",
    cursor: disabled ? "not-allowed" : "pointer",
  };
}

export const softDangerButtonStyle: CSSProperties = {
  padding: "13px 20px",
  borderRadius: "16px",
  border: "1px solid rgba(200, 77, 77, 0.18)",
  background: "rgba(255, 245, 245, 0.92)",
  color: "#b54747",
  fontWeight: 800,
  cursor: "pointer",
};

export const dangerGradientButtonStyle: CSSProperties = {
  padding: "13px 20px",
  borderRadius: "16px",
  border: "1px solid rgba(200, 77, 77, 0.18)",
  background: "linear-gradient(135deg, rgba(196, 62, 62, 0.96), rgba(224, 88, 88, 0.96))",
  color: "#fff",
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 12px 28px rgba(196, 62, 62, 0.18)",
};

export function feedbackBoxStyle(kind: FeedbackTone): CSSProperties {
  const palette = {
    info: {
      background: "rgba(15, 95, 215, 0.08)",
      color: "var(--muted)",
      border: "1px solid rgba(15, 95, 215, 0.12)",
    },
    error: {
      background: "rgba(217, 67, 67, 0.08)",
      color: "#b54747",
      border: "1px solid rgba(217, 67, 67, 0.12)",
    },
    success: {
      background: "rgba(41, 155, 93, 0.08)",
      color: "#21724a",
      border: "1px solid rgba(41, 155, 93, 0.12)",
    },
  }[kind];

  return {
    padding: "14px 16px",
    borderRadius: "16px",
    fontSize: "0.94rem",
    ...palette,
  };
}
