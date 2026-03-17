const mongoose = require("mongoose");

const patientSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
    },

    dob: {
      type: Date,
      required: true,
    },

    gender: {
      type: String,
      enum: ["Male", "Female", "Other"],
    },

    bloodGroup: String,

    height: Number,

    weight: Number,
  },
  { timestamps: true }
);

module.exports = mongoose.model("Patient", patientSchema);