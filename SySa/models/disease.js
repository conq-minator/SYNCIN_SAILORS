const mongoose = require("mongoose");

const diseaseSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
  },

  category: String,

  commonSymptoms: [String],

  riskLevel: String,

  summary: String,
});

module.exports = mongoose.model("Disease", diseaseSchema);