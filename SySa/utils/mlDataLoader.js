const fs = require('fs');
const path = require('path');

/**
 * Load disease data from ML backend and transform to MongoDB format
 */
function loadMLDiseaseData() {
  try {
    const mlDataPath = path.join(__dirname, '../../ai-health-ml(notyetadded)/data/disease_db.json');
    
    if (!fs.existsSync(mlDataPath)) {
      console.warn('ML disease database not found at:', mlDataPath);
      return [];
    }

    const rawData = fs.readFileSync(mlDataPath, 'utf-8');
    const diseases = JSON.parse(rawData);

    // Transform ML format to MongoDB format
    const transformedDiseases = diseases.map(d => ({
      name: d.disease,
      category: determineCategoryFromDisease(d.disease),
      commonSymptoms: (d.symptoms || []).map(s => s.replace(/_/g, ' ')), // Convert underscores to spaces
      riskLevel: determineRiskLevel(d.disease, d.symptoms),
      summary: generateSummary(d.disease, d.symptoms),
      verified: d.verified || false,
      source: d.source || 'unknown'
    }));

    console.log(`✓ Loaded ${transformedDiseases.length} diseases from ML backend`);
    return transformedDiseases;

  } catch (error) {
    console.error('Error loading ML disease data:', error.message);
    return [];
  }
}

/**
 * Determine disease category based on disease name
 */
function determineCategoryFromDisease(diseaseName) {
  const nameStr = diseaseName.toLowerCase();
  
  if (nameStr.includes('cold') || nameStr.includes('flu') || nameStr.includes('covid') || 
      nameStr.includes('cough') || nameStr.includes('asthma') || nameStr.includes('bronchi')) {
    return 'Respiratory';
  }
  if (nameStr.includes('heart') || nameStr.includes('cardiac') || nameStr.includes('fibrillation') || 
      nameStr.includes('hypertension') || nameStr.includes('blood')) {
    return 'Cardiovascular';
  }
  if (nameStr.includes('diabetes') || nameStr.includes('thyroid') || nameStr.includes('pancreas')) {
    return 'Endocrine';
  }
  if (nameStr.includes('stomach') || nameStr.includes('gastro') || nameStr.includes('diarrhea') || 
      nameStr.includes('nausea') || nameStr.includes('vomiting')) {
    return 'Gastrointestinal';
  }
  if (nameStr.includes('kidney') || nameStr.includes('urinary') || nameStr.includes('bladder')) {
    return 'Urinary';
  }
  if (nameStr.includes('skin') || nameStr.includes('rash') || nameStr.includes('dermatitis')) {
    return 'Dermatological';
  }
  if (nameStr.includes('eye') || nameStr.includes('vision') || nameStr.includes('glaucoma')) {
    return 'Ophthalmological';
  }
  if (nameStr.includes('anxiety') || nameStr.includes('depression') || nameStr.includes('mental')) {
    return 'Mental Health';
  }
  if (nameStr.includes('bone') || nameStr.includes('joint') || nameStr.includes('arthritis')) {
    return 'Musculoskeletal';
  }
  if (nameStr.includes('anaphylaxis') || nameStr.includes('allergy')) {
    return 'Allergic';
  }
  return 'General';
}

/**
 * Determine risk level based on disease characteristics
 */
function determineRiskLevel(diseaseName, symptoms) {
  const nameStr = diseaseName.toLowerCase();
  const symptomStr = (symptoms || []).join(' ').toLowerCase();
  
  // High risk conditions
  if (nameStr.includes('anaphylaxis') || nameStr.includes('sepsis') || 
      nameStr.includes('stroke') || nameStr.includes('heart attack') ||
      nameStr.includes('covid') || symptomStr.includes('difficulty_breathing')) {
    return 'high';
  }
  
  // Moderate risk conditions
  if (nameStr.includes('diabetes') || nameStr.includes('hypertension') || 
      nameStr.includes('asthma') || nameStr.includes('pneumonia') ||
      nameStr.includes('flu') || symptomStr.includes('fever')) {
    return 'moderate';
  }
  
  // Low risk conditions
  return 'low';
}

/**
 * Generate a brief summary for the disease
 */
function generateSummary(diseaseName, symptoms) {
  if (symptoms && symptoms.length > 0) {
    const cleanSymptoms = symptoms.slice(0, 3).map(s => s.replace(/_/g, ' '));
    return `${diseaseName} characterized by symptoms including ${cleanSymptoms.join(', ')}.`;
  }
  return `${diseaseName} is a medical condition that requires professional evaluation.`;
}

module.exports = {
  loadMLDiseaseData,
  determineCategoryFromDisease,
  determineRiskLevel
};
