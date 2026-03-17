const diseases = [
  {
    name: "Influenza (Flu)", // Ensure this is 'name', not 'disease' or 'title'
    category: "Respiratory",
    commonSymptoms: ["fever", "cough", "fatigue", "body ache"],
    riskLevel: "Moderate",
    summary: "A common viral infection that can be deadly, especially in high-risk groups."
  },
  {
    name: "Hypertension",
    category: "Cardiovascular",
    commonSymptoms: ["headache", "shortness of breath", "nosebleeds"],
    riskLevel: "High",
    summary: "A condition in which the force of the blood against the artery walls is too high."
  }
];

module.exports = diseases;