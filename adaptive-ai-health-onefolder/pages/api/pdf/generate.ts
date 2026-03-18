import type { NextApiRequest, NextApiResponse } from "next";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { z } from "zod";

// Schema matching the PDF service
const reportDataSchema = z.object({
  patient_name: z.string().min(1, "Patient name is required"),
  age: z.number().int().min(0).max(150, "Age must be between 0 and 150"),
  symptoms: z.array(z.string()).min(1, "At least one symptom is required"),
  prediction: z.string().min(1, "Prediction is required")
});

type ReportData = z.infer<typeof reportDataSchema>;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ message: "Method not allowed" });
  }

  try {
    // Validate the incoming data
    const validationResult = reportDataSchema.safeParse(req.body);
    if (!validationResult.success) {
      return res.status(400).json({
        error: "Invalid request data",
        details: validationResult.error.flatten()
      });
    }

    const data: ReportData = validationResult.data;

    // Create PDF document
    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage([595.28, 841.89]); // A4 size
    const { width, height } = page.getSize();

    // Embed fonts
    const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBoldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const helveticaObliqueFont = await pdfDoc.embedFont(StandardFonts.HelveticaOblique);

    const margin = 50;
    let yPosition = height - margin;

    // Helper function to draw text
    const drawText = (
      text: string,
      fontSize = 12,
      font = helveticaFont,
      color = rgb(0, 0, 0)
    ) => {
      page.drawText(text, {
        x: margin,
        y: yPosition,
        size: fontSize,
        font,
        color
      });
      yPosition -= fontSize + 8;
    };

    // Helper function to draw centered text
    const drawCenteredText = (
      text: string,
      fontSize = 12,
      font = helveticaFont,
      color = rgb(0, 0, 0)
    ) => {
      const textWidth = font.widthOfTextAtSize(text, fontSize);
      const x = (width - textWidth) / 2;
      page.drawText(text, {
        x,
        y: yPosition,
        size: fontSize,
        font,
        color
      });
      yPosition -= fontSize + 8;
    };

    // Header
    drawCenteredText("Medical Analysis Report", 24, helveticaBoldFont, rgb(0.1, 0.3, 0.6));
    yPosition -= 10;

    // Decorative line
    page.drawLine({
      start: { x: margin, y: yPosition },
      end: { x: width - margin, y: yPosition },
      thickness: 2,
      color: rgb(0.7, 0.7, 0.7)
    });
    yPosition -= 25;

    // Patient Information Section
    drawText("Patient Information", 14, helveticaBoldFont);
    yPosition -= 5;

    drawText(`Patient Name: ${data.patient_name}`, 12);
    drawText(`Age: ${data.age}`, 12);
    yPosition -= 10;

    // Symptoms Section
    drawText("Reported Symptoms:", 14, helveticaBoldFont);
    yPosition -= 5;

    for (const symptom of data.symptoms) {
      drawText(`• ${symptom}`, 11);
    }
    yPosition -= 10;

    // Prediction Box
    const boxHeight = 40;
    const boxY = yPosition - boxHeight;

    // Draw prediction box background
    page.drawRectangle({
      x: margin - 5,
      y: boxY,
      width: width - 2 * margin + 10,
      height: boxHeight,
      color: rgb(0.95, 0.95, 0.95),
      borderColor: rgb(0.1, 0.3, 0.6),
      borderWidth: 2
    });

    // Prediction text
    const predictionText = `AI PREDICTION: ${data.prediction.toUpperCase()}`;
    yPosition = boxY + 15;
    drawCenteredText(predictionText, 16, helveticaBoldFont, rgb(0.1, 0.3, 0.6));

    // Footer disclaimer
    yPosition = 60;
    const disclaimer = "Disclaimer: This is an AI-generated report for educational purposes. Consult a doctor for diagnosis.";
    page.drawText(disclaimer, {
      x: margin,
      y: yPosition,
      size: 9,
      font: helveticaObliqueFont,
      color: rgb(0.5, 0.5, 0.5)
    });

    // Generate PDF bytes
    const pdfBytes = await pdfDoc.save();

    // Set response headers
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="Medical_Report_${data.patient_name.replace(/\s+/g, '_')}.pdf"`);

    return res.status(200).send(Buffer.from(pdfBytes));

  } catch (error) {
    console.error("PDF generation error:", error);
    return res.status(500).json({
      error: "Failed to generate PDF",
      message: error instanceof Error ? error.message : "Unknown error"
    });
  }
}