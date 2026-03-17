// require("dotenv").config();


// const express = require("express");
// const app = express();
// const cors = require("cors");
// const mongoose = require("mongoose");
// // const Disease = require("./models/disease.js");
// // const Knowledge = require("./models/knowledge.js");
// // const Patient = require("./models/patient.js");
// // const Report = require("./models/report.js");
// // const Symptom = require("./models/symptom.js");

// // const MONGO_URL = "mongodb://127.0.0.1:27017/genericahh";

// // app.use(cors());

// // main()
// // .then(() => {
// //     console.log("connected to DB");
// // })
// // .catch((err) => {
// //     console.log(err);
// // }); 

// // async function main() {
// //     await mongoose.connect(MONGO_URL);
// // }

// app.get("/", (req, res) => {
//     res.send("Hi, i am root");
// });

// app.listen(8080, () => {
//     console.log("server is listening to port 8080");
// });

require("dotenv").config();
const express = require("express");
const app = express();
const path =require("path");
const cors = require("cors");
const axios = require("axios");
const Disease = require("./models/disease");

const connectDB = require("./config/db");

const patientRoutes = require("./routes/patientRoutes");
const reportRoutes = require("./routes/reportRoutes");
const diseaseRoutes = require("./routes/diseaseRoutes");

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.use(express.static(path.join(__dirname, "public")));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());


connectDB();

app.use(cors());
app.use(express.json());

app.use("/api/patients", patientRoutes);
app.use("/api/reports", reportRoutes);
app.use("/api/diseases", diseaseRoutes);

const PORT = process.env.PORT || 5000;

app.get("/", (req, res) => {
    res.render("intake");
});

app.post("/predict", async (req, res) => {
    try {
        const { symptoms, name } = req.body;
        if (!symptoms) return res.redirect("/");

        // Split input into array: "fever, cough" -> ["fever", "cough"]
        const userSymptoms = symptoms.toLowerCase().split(",").map(s => s.trim());

        // Fetch diseases directly from your DB (No axios needed here)
        const allDiseases = await Disease.find();

        const results = allDiseases.map(disease => {
            // Find matches between user input and DB commonSymptoms
            const matches = disease.commonSymptoms.filter(s => 
                userSymptoms.includes(s.toLowerCase())
            );
            
            // Calculate confidence
            const confidence = disease.commonSymptoms.length > 0 
                ? Math.round((matches.length / disease.commonSymptoms.length) * 100) 
                : 0;

            return {
                disease: disease.name,
                confidence: confidence,
                summary: disease.summary,
                riskLevel: disease.riskLevel
            };
        }).filter(r => r.confidence > 0) // Only show relevant results
          .sort((a, b) => b.confidence - a.confidence);

        res.render("results", { cards: results, userName: name });

    } catch (err) {
        console.error("Prediction Error:", err);
        res.status(500).send("The AI engine hit a snag. Check your console!");
    }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});