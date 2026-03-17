from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import tempfile
import os
import pdfplumber

app = FastAPI()

# --- THE CORS BOUNCER ---
# This tells your backend: "Yes, it is safe to let the frontend website talk to me."
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS (The Data Contract for the Backend) ---
class ReportData(BaseModel):
    patient_name: str
    age: int
    symptoms: List[str]
    prediction: str

# --- HELPER FUNCTION ---
def remove_file(path: str):
    """Deletes the temporary file after it's sent to the user."""
    try:
        os.unlink(path)
    except Exception:
        pass

# --- ROUTES ---

@app.get("/")
def read_root():
    return {"message": "PDF Service is officially running!"}

@app.post("/generate-pdf")
def generate_pdf(data: ReportData, background_tasks: BackgroundTasks):
    # 1. Create a safe temporary file
    fd, file_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd) 

    try:
        # 2. Setup the Canvas (Your drawing board)
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        # 3. Draw Header 
        c.setFont("Helvetica-Bold", 22)
        c.setFillColorRGB(0.1, 0.3, 0.6) # Professional Dark Blue
        c.drawCentredString(width / 2, height - inch, "Medical Analysis Report")
        
        # Horizontal accent line
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(inch, height - 1.2 * inch, width - inch, height - 1.2 * inch)

        # 4. Patient Information Section
        c.setFillColorRGB(0, 0, 0) # Reset to black
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, height - 1.6 * inch, "Patient Name: ")
        c.setFont("Helvetica", 12)
        c.drawString(inch + 100, height - 1.6 * inch, data.patient_name)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, height - 1.9 * inch, "Age: ")
        c.setFont("Helvetica", 12)
        c.drawString(inch + 100, height - 1.9 * inch, str(data.age))

        # 5. Symptoms List
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, height - 2.4 * inch, "Reported Symptoms:")
        
        text_obj = c.beginText()
        text_obj.setTextOrigin(inch + 0.2 * inch, height - 2.7 * inch)
        text_obj.setFont("Helvetica", 11)
        text_obj.setLeading(15) # Space between lines
        
        for symptom in data.symptoms:
            text_obj.textLine(f"• {symptom}")
        c.drawText(text_obj)

        # 6. Final Prediction Box
        list_bottom = height - (2.8 * inch + (15 * len(data.symptoms)))
        
        c.setStrokeColorRGB(0.1, 0.3, 0.6)
        c.rect(inch - 0.1*inch, list_bottom - 0.4*inch, width - 2*inch + 0.2*inch, 0.7*inch, fill=0)
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, list_bottom - 0.1*inch, f"AI PREDICTION: {data.prediction.upper()}")

        # 7. Footer / Disclaimer
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(width / 2, 0.7 * inch, "Disclaimer: This is an AI-generated report for educational purposes. Consult a doctor for diagnosis.")

        c.showPage()
        c.save()

        # 8. Tell FastAPI to delete the file AFTER sending it
        background_tasks.add_task(remove_file, file_path)

        # 9. Send the file to the browser
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"Medical_Report_{data.patient_name}.pdf"
        )

    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}


@app.post("/extract-text")
async def extract_text_from_pdf(file: UploadFile = File(...)):
    """
    Takes an uploaded PDF and turns it into raw text for the AI/ML team.
    """
    try:
        with pdfplumber.open(file.file) as pdf:
            all_text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    all_text += extracted + "\n"
        
        return {
            "filename": file.filename,
            "content": all_text.strip() if all_text else "No text found in PDF."
        }
    except Exception as e:
        return {"error": f"Could not parse PDF: {str(e)}"}