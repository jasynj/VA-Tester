// signup.js
const BASE_URL = "http://127.0.0.1:5000";

document.getElementById("signupForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("signupEmail").value;
  const password = document.getElementById("signupPassword").value;

  // You can collect and send firstName, lastName, dob too if backend is ready
  const res = await fetch(`${BASE_URL}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  alert(data.message || data.error);
  if (data.message === "Signup successful") {
    window.location.href = "login.html";
  }
});
