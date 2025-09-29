const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");
const twilio = require("twilio");

const app = express();
app.use(cors());
app.use(bodyParser.json());

// 🔑 Replace with your Twilio credentials
const accountSid = "YOUR_TWILIO_ACCOUNT_SID";
const authToken = "YOUR_TWILIO_AUTH_TOKEN";
const client = twilio(accountSid, authToken);

// Bulk SMS endpoint
app.post("/send-sms", async (req, res) => {
  const { numbers, message } = req.body;

  if (!numbers || !message) {
    return res.status(400).json({ error: "Missing numbers or message" });
  }

  let results = [];

  for (let number of numbers) {
    try {
      const msg = await client.messages.create({
        body: message,
        from: "YOUR_TWILIO_PHONE_NUMBER", // Replace with Twilio number
        to: number,
      });

      results.push({
        number,
        status: "Sent ✅",
        sid: msg.sid,
        error: null,
      });
    } catch (error) {
      results.push({
        number,
        status: "Failed ❌",
        sid: null,
        error: error.message,
      });
    }
  }

  res.json({ results });
});

app.listen(5000, () => console.log("🚀 Backend running on port 5000"));
