async function sendMsg() {
  const msg = document.getElementById("msg").value;

  await fetch("/send_message", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      sender: localStorage.getItem("email"),
      receiver: "therapist@example.com",
      message: msg
    })
  });

  loadMessages();
}

async function loadMessages() {
  const res = await fetch("/get_messages", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      user1: localStorage.getItem("email"),
      user2: "therapist@example.com"
    })
  });

  const data = await res.json();

  let output = "";

  data.messages.forEach(m => {
    output += `<p><b>${m[0]}:</b> ${m[1]}</p>`;
  });

  document.getElementById("chatBox").innerHTML = output;
}

loadMessages();