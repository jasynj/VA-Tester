# 👁️ EyecareLive Vision Test App

This is a lightweight web application inspired by the EyecareLive Vision Test, designed to help users assess their visual acuity from home using a laptop or desktop paired with a smartphone. The application guides users through the testing process and allows them to securely save and view their test results.

This project was developed as a group assignment to apply full-stack web development skills using **Python**, **Flask**, **SQLAlchemy**, and standard web technologies (**HTML**, **CSS**, **JavaScript**).  
> _It’s intended as a preliminary screening tool, not a replacement for a full eye exam._

---

## 🌐 Live Demo (Optional)

[🔗 Live Demo — Test Your Vision Now ](https://va-tester-b127.onrender.com)

---

## 🚀 Features

- 👤 **User Authentication** – Secure signup and login system with password hashing and session handling to protect user data.
- 📱 **Mobile Pairing** – Generates a QR code that allows users to connect their smartphone as a remote control for the vision test, enhancing the multi-device experience.
- 🔡 **Optotype Test** – Presents rotating "C" (Landolt C) optotypes requiring directional input from the user to assess visual acuity.
- 🧠 **Real-Time Feedback** – Guides users during the test, including indicators for maintaining the correct viewing distance (planned buzz).
- 📊 **Result Storage** – Saves each user's test results in the database with timestamps for easy tracking and future reference.
- 📂 **Results Dashboard** – Provides a personalized view of previously saved vision test results for each logged-in user.
- 💻 **Cross-Device Friendly Interface** – Simple and responsive web design compatible with both desktop and mobile devices.
- 🔒 **Secure Session Management** – User sessions maintained securely with automatic logout functionality to ensure data privacy.
- 🖼️ **QR Code Test Access** – Fast access to the test setup page via generated QR codes, making it easy to pair and begin testing quickly.
- 🧪 **Test Completion Feedback** – Confirms successful test submission and result saving with animated success modals (e.g., pop-up confirmation).

---

## 🛠️ Tech Stack

| Technology               | Purpose                               |
|---------------------------|---------------------------------------|
| **Python, Flask**          | Backend server, RESTful routes       |
| **SQLite**                 | Local database for storing users and results |
| **SQLAlchemy**             | ORM for database interaction        |
| **HTML, CSS, JavaScript**  | Frontend forms, test flow, result display |
| **Werkzeug Security**      | Password hashing and verification   |
| **Flask-CORS**             | Handle cross-origin requests        |
| **qrcode, Pillow**         | QR code generation for test linking |

---

## 🌐 Backend Routes Overview

| Route             | Method | Description                           |
|-------------------|--------|---------------------------------------|
| `/signup`         | POST   | Registers a new user                  |
| `/login`          | POST   | Authenticates existing users          |
| `/save_result`    | POST   | Saves a user's vision test result     |
| `/my_results`     | GET    | Displays the logged-in user's saved results |
| `/logout`         | GET    | Logs the user out and clears session  |
| `/generate_qr`    | GET    | Creates a QR code with test instructions |

---

## 🖌️ Frontend Structure

- **Authentication Pages:** Simple sign-up and login forms.
- **Test Instruction Page:** Includes QR code display and test guidance.
- **Results Page:** Displays past test results for the logged-in user.
- **Styling:** Clean blue-and-white color scheme, responsive design using CSS.

---

## 💡 Future Development Ideas

- Add visual acuity scoring logic with automatic interpretation of results.
- Enable test result deletion and result filtering by date.
- Deploy the app to a cloud platform for public use (e.g., Heroku, Render).
- Add email verification for account registration.
- Improve mobile test-taking experience with additional device support.

---
