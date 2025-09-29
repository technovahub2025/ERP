document.getElementById("sendBtn").addEventListener("click", async () => {
  const csvFile = document.getElementById("csvFile").files[0];
  const attachment = document.getElementById("attachment").files[0];
  const subject = document.getElementById("subject").value;
  const message = document.getElementById("message").value;
  const scheduleTime = document.getElementById("scheduleTime").value;

  if (!csvFile || !subject || !message) {
    alert("Please fill all required fields!");
    return;
  }

  // Read CSV
  const reader = new FileReader();
  reader.onload = async function (e) {
    const text = e.target.result;
    const lines = text.split("\n").map(l => l.trim()).filter(l => l);
    const emails = lines.map(row => {
      const [name, email] = row.split(",");
      return { name, email };
    });

    // Prepare form data
    const formData = new FormData();
    formData.append("emails", JSON.stringify(emails));
    formData.append("subject", subject);
    formData.append("message", message);
    formData.append("scheduleTime", scheduleTime);
    if (attachment) formData.append("attachment", attachment);

    // Send to backend
    const res = await fetch("http://localhost:3001/send-emails", {
      method: "POST",
      body: formData
    });

    const result = await res.text();
    document.getElementById("status").innerText = result;
  };

  reader.readAsText(csvFile);
});
