// Toggle between the signup and login forms
function toggleForms() {
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const toggleLink = document.querySelector(".toggle-link");

  if (loginForm.classList.contains("hidden")) {
    // Switch to signup form
    loginForm.classList.remove("hidden");
    signupForm.classList.add("hidden");
    toggleLink.textContent = "Don't have an account? Sign Up";
  } 
  else {
    // Switch to login form
    signupForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
    toggleLink.textContent = "Already have an account? Log In";

  }
}


// Signup function
function signupUser(e) {
  e.preventDefault();

  const firstName = document.getElementById("firstName").value.trim();
  const lastName = document.getElementById("lastName").value.trim();
  const dob = document.getElementById("dob").value.trim();
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value.trim();

  if (!firstName || !lastName || !dob || !email || !password) {
    alert("Please fill out all the fields.");
    return;
  }

  fetch('http://127.0.0.1:5050/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      firstName,
      lastName,
      dob,
      email,
      password
    })
  })
  .then(response => {
    if (response.ok) {
      return response.json();
    } else {
      return response.json().then(data => { throw new Error(data.error || "Signup error"); });
    }
  })
  .then(data => {
    alert(data.message);
    toggleForms(); // Switch to login form upon successful signup
  })
  .catch(err => {
    alert("Signup failed: " + err.message);
  });
}


// Login function
function loginUser(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value.trim();

  if (!email || !password) {
    alert("Please provide email and password.");
    return;
  }

  fetch('http://127.0.0.1:5050/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // include cookies to maintain session
    body: JSON.stringify({ email, password })
  })
  .then(response => {
    if (response.ok) {
      return response.json();
    } else {
      return response.json().then(data => { throw new Error(data.error || "Login error"); });
    }
  })
  .then(data => {
    alert(data.message);
    // Optionally, redirect or fetch additional user data here
    window.location.href = "http://127.0.0.1:5050/dashboard";
  })
  .catch(err => {
    alert("Login failed: " + err.message);
  });
}


// Attach event listeners to handle form submissions
document.getElementById("signup-form").addEventListener("submit", signupUser);
document.getElementById("login-form").addEventListener("submit", loginUser);
