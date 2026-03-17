const Patient = require("../models/patient");

exports.createPatient = async (req, res) => {
  try {
    const patient = new Patient(req.body);
    await patient.save();

    res.status(201).json(patient);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getPatient = async (req, res) => {
  try {
    const patient = await Patient.findById(req.params.id);
    res.json(patient);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};