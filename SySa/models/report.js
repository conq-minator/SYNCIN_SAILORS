const mongoose = require("mongoose");

const reportSchema = new mongoose.Schema(
  {
    patientId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Patient",
      required: true,
    },

    vitals: {
      bloodPressure: String,
      bloodSugar: Number,
      heartRate: Number,
      temperature: Number,
    },

    lifestyle: {
      sleepHours: Number,
      stressLevel: String,
      activityLevel: String,
    },

    biasInput: String,
  },
  { timestamps: true }
);

module.exports = mongoose.model("Report", reportSchema);