const mongoose = require("mongoose");

const knowledgeBaseSchema = new mongoose.Schema({
  disease: {
    type: String,
    required: true,
  },

  symptomWeights: {
    type: Map,
    of: Number,
  },

  contradictions: [String],
});

module.exports = mongoose.model("KnowledgeBase", knowledgeBaseSchema);