// config/db.js
const mongoose = require("mongoose");

async function connectDB() {
    try {
        // CHANGED FROM MONGO_URL TO MONGO_URI
        await mongoose.connect(process.env.MONGO_URI); 
        console.log("✅ Server connected to MongoDB");
    } catch (err) {
        console.log("❌ Database connection error:", err.message);
        process.exit(1);
    }
}

module.exports = connectDB;


// const mongoose = require("mongoose");

// main()
// .then(() => {
//     console.log("connected to DB");
// })
// .catch((err) => {
//     console.log(err);
// }); 

// module.exports = async function main() {
//     await mongoose.connect(MONGO_URL);
// }

// const connectDB = async () => {
//   try {
//     await mongoose.connect(process.env.MONGO_URI, {
//       useNewUrlParser: true,
//       useUnifiedTopology: true,
//     });

//     console.log("MongoDB Connected");
//   } catch (error) {
//     console.error("Database connection error:", error);
//     process.exit(1);
//   }
// };
