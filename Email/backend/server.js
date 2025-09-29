const express = require("express");
const multer = require("multer");
const csv = require("csv-parser");
const fs = require("fs");
const nodemailer = require("nodemailer");
const cors = require("cors");

const app = express();
const PORT = 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Multer for file upload
const upload = multer({ dest: "uploads/" });

// Nodemailer transporter (use Gmail or SMTP)
const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: "yourgmail@gmail.com", // ✅ replace with your email
    pass: "your-app-password"    // ✅ replace with app password
  }
});

// Endpoint to upload CSV and send emails
app.post("/send-emails", upload.single("file"), (req, res) => {
  const filePath = req.file.path;
  const subject = req.body.subject;
  const message = req.body.message;

  let recipients = [];

  fs.createReadStream(filePath)
    .pipe(csv())
    .on("data", (row) => {
      if (row.email) {
        recipients.push(row.email);
      }
    })
    .on("end", async () => {
      try {
        for (let email of recipients) {
          await transporter.sendMail({
            from: '"TechnovaHub" <yourgmail@gmail.com>',
            to: email,
            subject: subject,
            text: message
          });
        }

        fs.unlinkSync(filePath); // cleanup
        res.json({ success: true, message: "Emails sent successfully!" });
      } catch (err) {
        console.error("Error sending emails:", err);
        res.status(500).json({ success: false, error: err.message });
      }
    });
});

app.listen(PORT, () => {
  console.log(`✅ Server running on http://localhost:${PORT}`);
});
