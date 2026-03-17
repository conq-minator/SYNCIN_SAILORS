const express = require("express");
const router = express.Router();
const diseaseController = require("../controllers/diseaseController");

router.get("/", diseaseController.getAllDiseases);
router.get("/:id", diseaseController.getDiseaseById);

module.exports = router;