const mongoose = require("mongoose");

const diseaseSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    unique: true,
    trim: true
  },

  category: {
    type: String,
    default: "General"
  },

  commonSymptoms: [String],

  riskLevel: {
    type: String,
    enum: ['low', 'moderate', 'high'],
    default: 'moderate',
    lowercase: true
  },

  summary: {
    type: String,
    default: ""
  },

  // Additional fields from ML backend
  verified: {
    type: Boolean,
    default: false
  },

  source: {
    type: String,
    default: "unknown",
    enum: ['database', 'online', 'unknown']
  }
}, { timestamps: true });

module.exports = mongoose.model("Disease", diseaseSchema);