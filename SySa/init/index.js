const mongoose = require("mongoose");
const path = require("path");
// This looks one level up (..) from the current 'init' folder to find .env
require("dotenv").config({ path: path.join(__dirname, "../.env") }); 

const Disease = require("../models/disease");
const data = require("./data.js"); // Your dummy data file

async function seedDB() {
    try {
        // Use the EXACT name from your .env (you have MONGO_URI in your .env)
        const connectionString = process.env.MONGO_URI; 
        
        if (!connectionString) {
            throw new Error("MONGO_URI is undefined. Check if your .env variable name matches!");
        }

        await mongoose.connect(connectionString);
        console.log("✅ Connected to DB for seeding...");

        await Disease.deleteMany({});
        await Disease.insertMany(data);
        
        console.log("🚀 Database seeded successfully with dummy data!");
    } catch (err) {
        console.error("❌ Seeding Error:", err.message);
    } finally {
        mongoose.connection.close();
    }
}

seedDB();