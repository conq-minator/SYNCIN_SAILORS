import type { NextApiRequest, NextApiResponse } from "next";
import formidable from "formidable";
import { promises as fs } from "fs";

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ message: "Method not allowed" });
  }

  try {
    const form = formidable({
      maxFileSize: 10 * 1024 * 1024, // 10MB limit
      keepExtensions: true,
    });

    const [fields, files] = await form.parse(req);

    const file = files.file?.[0];
    if (!file) {
      return res.status(400).json({
        error: "No file uploaded",
        message: "Please upload a PDF file with the field name 'file'"
      });
    }

    if (!file.mimetype?.includes('pdf') && !file.originalFilename?.toLowerCase().endsWith('.pdf')) {
      return res.status(400).json({
        error: "Invalid file type",
        message: "Only PDF files are allowed"
      });
    }

    // For now, return basic file info since full text extraction requires more complex setup
    // This can be enhanced later with proper PDF parsing libraries
    const fileStats = await fs.stat(file.filepath);
    await fs.unlink(file.filepath); // Clean up

    return res.status(200).json({
      filename: file.originalFilename || "uploaded.pdf",
      content: `PDF file "${file.originalFilename}" uploaded successfully. Text extraction feature is available but requires additional PDF parsing setup. File size: ${fileStats.size} bytes.`,
      metadata: {
        size: fileStats.size,
        mimetype: file.mimetype,
        uploaded: true
      },
      note: "Full text extraction will be implemented with proper PDF parsing libraries in production."
    });

  } catch (error) {
    console.error("PDF processing error:", error);
    return res.status(500).json({
      error: "Failed to process PDF",
      message: error instanceof Error ? error.message : "Unknown error"
    });
  }
}