const express = require("express");
const nodemailer = require("nodemailer");
const multer = require("multer");
const bodyParser = require("body-parser");
const cors = require("cors");
const fs = require("fs");

const app = express();
app.use(cors());
app.use(bodyParser.json());

const upload = multer({ dest: "uploads/" });

// Gmail SMTP setup
let transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: "sakthivelraja3902@gmail.com", // your email
    pass: "inuq aumb aizv crvv" // Gmail App Password (not normal password)
  }
});

app.post("/send-emails", upload.single("attachment"), async (req, res) => {
  const { subject, message, scheduleTime } = req.body;
  const emails = JSON.parse(req.body.emails);

  let mailOptions = {
    from: "technovahubcareer@gmail.com",
    subject: subject,
    text: message,
    attachments: req.file ? [{ filename: req.file.originalname, path: req.file.path }] : []
  };

  // Schedule
  const delay = new Date(scheduleTime) - new Date();
  setTimeout(() => {
    emails.forEach(({ name, email }) => {
      transporter.sendMail({ ...mailOptions, to: email }, (err, info) => {
        if (err) console.error(err);
        else console.log("Sent to:", email);
      });
    });
  }, delay > 0 ? delay : 0);

  res.send("✅ Emails scheduled successfully!");
});

app.listen(3001, () => console.log("Server running on http://localhost:3001"));
