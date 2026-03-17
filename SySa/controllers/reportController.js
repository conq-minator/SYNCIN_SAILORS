const Report = require("../models/report");

exports.createReport = async (req, res) => {
  try {
    const report = new Report(req.body);
    await report.save();

    res.status(201).json(report);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getReportsByPatient = async (req, res) => {
  try {
    const reports = await Report.find({
      patientId: req.params.patientId,
    });

    res.json(reports);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};