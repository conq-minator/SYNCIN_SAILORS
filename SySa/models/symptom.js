const mongoose = require("mongoose");

const symptomSchema = new mongoose.Schema({
  reportId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Report",
  },

  symptoms: [
    {
      name: String,
      frequency: String,
      duration: String,
      intensity: String,
      onset: String,
    },
  ],
});

module.exports = mongoose.model("Symptom", symptomSchema);