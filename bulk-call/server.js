const express = require("express");
const multer = require("multer");
const csvParser = require("csv-parser");
const fs = require("fs");
const dotenv = require("dotenv");
const cors = require("cors");
const twilio = require("twilio");

dotenv.config();

const app = express();
const upload = multer({ dest: "uploads/" });
app.use(cors());
app.use(express.json());

const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
const audioUrl = "https://public-qql5f5njy-sakthivels-projects-b92e2be4.vercel.app/offers.mp3";

app.post("/api/bulk-call", upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ status: "Failed", error: "No file uploaded." });
  }

  const filePath = req.file.path;
  const results = [];

  fs.createReadStream(filePath)
    .pipe(csvParser())
    .on('data', (data) => results.push(data))
    .on('end', async () => {
      let success = 0;
      let failed = 0;
      let details = [];

      for (const entry of results) {
        const rawPhone = entry.phone || "";
        const phone = rawPhone.startsWith('+') ? rawPhone : `+91${rawPhone.replace(/\D/g, '')}`;

        try {
          const call = await client.calls.create({
            twiml: `<Response><Play>${audioUrl}</Play></Response>`,
            to: phone,
            from: process.env.TWILIO_PHONE
          });
          success++;
          details.push({ number: phone, status: 'Success', callSid: call.sid });
          console.log(`✅ Success: ${phone} → ${call.sid}`);
        } catch (error) {
          failed++;
          details.push({ number: phone, status: 'Failed', error: error.message });
          console.error(`❌ Failed: ${phone} → ${error.message}`);
        }
      }

      fs.unlinkSync(filePath); // Clean up
      res.json({ success, failed, details });
    });
});
require('dotenv').config();
const PORT = process.env.PORT || 3001;

app.listen(PORT, () => {
  console.log(`🚀 Account 2 server running on port ${PORT}`);
});
