import mongoose, { Schema, Document, Model } from 'mongoose';

// 1. Define the Interface (The blueprint)
export interface IDisease extends Document {
  name: string;
  category: string;
  commonSymptoms: string[];
  riskLevel: 'low' | 'moderate' | 'high'; // Matches your friend's types
  summary: string;
  guidance?: string;
}

// 2. Define the Schema
const DiseaseSchema: Schema = new Schema({
  name: { type: String, required: true, unique: true },
  category: { type: String, required: true },
  commonSymptoms: [{ type: String }],
  riskLevel: { 
    type: String, 
    enum: ['low', 'moderate', 'high'], 
    default: 'moderate' 
  },
  summary: { type: String, required: true },
  guidance: { type: String }
});

// 3. Export the Model (Using a singleton pattern for Next.js)
const Disease: Model<IDisease> = mongoose.models.Disease || mongoose.model<IDisease>('Disease', DiseaseSchema);

export default Disease;
