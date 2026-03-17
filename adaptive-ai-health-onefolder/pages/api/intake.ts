import type { NextApiRequest, NextApiResponse } from "next";
import { intakeSchema } from "@/lib/validation";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ message: "Method not allowed" });
  }

  const parsed = intakeSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      message: "Invalid intake payload",
      details: parsed.error.flatten()
    });
  }

  return res.status(200).json({
    ok: true,
    intakeId: `intake_${Date.now()}`
  });
}

