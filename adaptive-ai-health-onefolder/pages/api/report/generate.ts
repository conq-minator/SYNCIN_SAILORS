import type { NextApiRequest, NextApiResponse } from "next";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { intakeSchema } from "@/lib/validation";
import type { PredictResponse } from "@/lib/types";

type Body = {
  intake: unknown;
  predictions: PredictResponse["predictions"];
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ message: "Method not allowed" });
  }

  const body = req.body as Body;
  const intakeParsed = intakeSchema.safeParse(body.intake);
  if (!intakeParsed.success) {
    return res.status(400).json({
      message: "Invalid intake payload",
      details: intakeParsed.error.flatten()
    });
  }

  const intake = intakeParsed.data;
  const predictions = Array.isArray(body.predictions) ? body.predictions : [];

  const pdf = await PDFDocument.create();
  const page = pdf.addPage([595.28, 841.89]); // A4
  const { width, height } = page.getSize();

  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const fontBold = await pdf.embedFont(StandardFonts.HelveticaBold);

  const margin = 48;
  let y = height - margin;

  const drawText = (text: string, size = 11, bold = false, color = rgb(0.05, 0.09, 0.16)) => {
    page.drawText(text, {
      x: margin,
      y,
      size,
      font: bold ? fontBold : font,
      color
    });
    y -= size + 10;
  };

  drawText("Adaptive AI Health Intelligence System", 18, true);
  drawText("Health Summary (Assistive)", 13, true, rgb(0.17, 0.42, 0.69));
  y -= 6;

  drawText(
    "Disclaimer: This system provides assistive insights and does not replace medical diagnosis.",
    10,
    false,
    rgb(0.29, 0.36, 0.44)
  );
  drawText(
    "Confidence explanation: Confidence reflects pattern matching with known data.",
    10,
    false,
    rgb(0.29, 0.36, 0.44)
  );

  y -= 10;
  page.drawLine({
    start: { x: margin, y },
    end: { x: width - margin, y },
    thickness: 1,
    color: rgb(0.90, 0.93, 0.96)
  });
  y -= 18;

  drawText("Patient info", 12, true);
  drawText(`Name: ${intake.personalInfo.fullName || "—"}`, 11);
  drawText(`DOB: ${intake.personalInfo.dob || "—"}`, 11);
  drawText(`Gender: ${intake.personalInfo.gender}`, 11);
  drawText(`Blood group: ${intake.personalInfo.bloodGroup || "—"}`, 11);

  y -= 8;
  drawText("Symptoms (reported)", 12, true);
  const symptoms = intake.symptoms
    .map((s) => `${s.name || "—"} (duration ${s.durationDays}d, intensity ${s.intensity}/5, freq ${s.frequencyPerDay}/day)`)
    .slice(0, 12);
  for (const line of symptoms) drawText(`• ${line}`, 10);

  if (intake.assumption?.trim()) {
    y -= 6;
    drawText("User assumption", 12, true);
    drawText(intake.assumption.trim(), 10);
  }

  y -= 8;
  drawText("Top predictions (assistive)", 12, true);
  for (const p of predictions.slice(0, 8)) {
    drawText(`• ${p.diseaseName} — ${Math.round(p.confidence)}% (${p.risk.toUpperCase()} risk)`, 10);
  }

  const bytes = await pdf.save();
  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", "attachment; filename=health-summary.pdf");
  return res.status(200).send(Buffer.from(bytes));
}

