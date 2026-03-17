const Disease = require("../models/disease");

exports.getAllDiseases = async (req, res) => {
  try {
    const diseases = await Disease.find();
    res.json(diseases);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getDiseaseById = async (req, res) => {
  try {
    const disease = await Disease.findById(req.params.id);
    res.json(disease);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};