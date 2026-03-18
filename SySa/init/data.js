const { loadMLDiseaseData } = require('../utils/mlDataLoader');

// Load diseases from ML backend, or use fallback
const mlDiseases = loadMLDiseaseData();

// Fallback diseases (in case ML data is not available)
const fallbackDiseases = [
  {
    name: "Influenza (Flu)",
    category: "Respiratory",
    commonSymptoms: ["fever", "cough", "fatigue", "body ache"],
    riskLevel: "moderate",
    summary: "A common viral infection that can be deadly, especially in high-risk groups."
  },
  {
    name: "Hypertension",
    category: "Cardiovascular",
    commonSymptoms: ["headache", "shortness of breath", "nosebleeds"],
    riskLevel: "high",
    summary: "A condition in which the force of the blood against the artery walls is too high."
  }
];

// Use ML data if available, otherwise use fallback
const diseases = mlDiseases.length > 0 ? mlDiseases : fallbackDiseases;

module.exports = diseases;