const twilio = require("twilio");

const client = new twilio(process.env.TWILIO_SID, process.env.TWILIO_AUTH_TOKEN);

module.exports.sendSMS = async (to, body) => {
  return client.messages.create({
    body,
    from: process.env.TWILIO_PHONE, // Twilio number
    to: "+91" + to  // Add country code
  });
};
