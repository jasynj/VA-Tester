// login.js
const BASE_URL = "http://127.0.0.1:5000";

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;

  const res = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // retain session on backend
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();

  if (data.message === "Login successful") {
    // ✅ Save to localStorage
    localStorage.setItem("isLoggedIn", "true");
    localStorage.setItem("userEmail", email);

    alert("Login successful!");
    window.location.href = "test.html";
  } else {
    alert(data.error || "Login failed");
  }
});
