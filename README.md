# 🏥 Syncin Sailors: Adaptive AI Health

An intelligent **Disease Detection** system utilizing Machine Learning and NLP to diagnose diseases based on user symptoms, calculate confidence scores, and provide robust medical insights. Built for our Hackathon! 🚀

## ✨ Features
- **Intelligent Symptom Analysis**: Uses AI/ML to analyze patient symptoms and predict the likelihood of various diseases.
- **Multimodal Medical Intake**: A beautiful, user-friendly frontend to collect medical history and symptoms (minimum 4-5 symptoms for higher accuracy).
- **High Confidence Predictions**: Integrates with robust machine learning models to provide predictions filtered by a minimum confidence score (> 60%).
- **PDF Medical Reports Processing**: Integrated Python microservice for handling PDF health reports and extracting insights.
- **Scalable Architecture**: Microservices-based backend separated cleanly into Node-based general APIs and Python-based ML APIs.

## 🏗️ Architecture & Tech Stack

The project is structured into four main components:

### 1. **Next.js Frontend (`adaptive-ai-health-onefolder`)**
The user-facing portal built with modern web technologies.
- **Framework**: Next.js 15, React 19
- **Styling**: Tailwind CSS
- **Features**: Responsive UI, Zod schema validations, interactive forms.

### 2. **Node.js Gateway Backend (`SySa`)**
The central orchestrator and database manager.
- **Framework**: Express.js, Node.js
- **Database**: MongoDB (via Mongoose)
- **Features**: API routing, data validation with Joi, EJS templates.

### 3. **AI/ML Engine (`ai-health-ml`)**
The brain of the disease detection system.
- **Framework**: FastAPI (Python)
- **ML Stack**: Scikit-Learn, Pandas, NumPy, spaCy
- **Features**: NLP-based symptom extraction, robust model pipelines, trained inference models.

### 4. **PDF Parsing Service (`pdfService`)**
A specialized python service handling document intelligence.
- **Stack**: Python, specialized parsers.
- **Features**: Extracts medical histories from uploaded PDF documents to aid in diagnosis.

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- MongoDB running locally or via Atlas.

### Running the Project

#### 1. Setup the Next.js Frontend
```bash
cd adaptive-ai-health-onefolder
npm install
npm run dev
```

#### 2. Setup the Node Backend
```bash
cd SySa
npm install
npm run dev
```

#### 3. Setup the AI Engine
```bash
cd ai-health-ml
pip install -r requirements.txt
uvicorn main:app --reload
```

#### 4. Setup PDF Service
```bash
cd pdfService
pip install -r requirements.txt
python main.py
```

## 🔐 Environment Variables
Make sure to add a `.env` file referencing your MongoDB URL and other required local API endpoints. 

---
*Built with ❤️ by the Syncin Sailors for the Hackathon.*