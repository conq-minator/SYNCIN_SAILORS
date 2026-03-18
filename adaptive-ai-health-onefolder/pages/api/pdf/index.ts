import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ message: "Method not allowed" });
  }

  return res.status(200).json({
    message: "PDF Service is running!",
    version: "1.0.0",
    endpoints: {
      "GET /api/pdf": "Service status",
      "POST /api/pdf/generate": "Generate medical report PDF",
      "POST /api/pdf/extract-text": "Extract text from PDF file"
    },
    features: [
      "Medical report PDF generation",
      "PDF text extraction",
      "Input validation",
      "Professional formatting"
    ]
  });
}