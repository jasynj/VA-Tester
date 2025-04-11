// Toggle between dark and light themes (if needed)
function toggleTheme() {
  document.body.classList.toggle("dark-mode");
}

// Toggle between the signup and login forms
function toggleForms() {
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const toggleLink = document.querySelector(".toggle-link");

  if (signupForm.classList.contains("hidden")) {
    // Switch to signup form
    signupForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
    toggleLink.textContent = "Already have an account? Log In";
  } else {
    // Switch to login form
    signupForm.classList.add("hidden");
    loginForm.classList.remove("hidden");
    toggleLink.textContent = "Don't have an account? Sign Up";
  }
}

// Signup function
function signupUser(e) {
  e.preventDefault();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value.trim();

  if (!email || !password) {
    alert("Please provide email and password.");
    return;
  }
  fetch('http://127.0.0.1:5000/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password })
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

  fetch('http://127.0.0.1:5000/login', {
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
  })
  .catch(err => {
    alert("Login failed: " + err.message);
  });
}

// Attach event listeners to handle form submissions
document.getElementById("signup-form").addEventListener("submit", signupUser);
document.getElementById("login-form").addEventListener("submit", loginUser);
