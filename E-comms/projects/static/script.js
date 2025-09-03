// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", () => {
  // ✅ Firebase Auth instance
  const auth = firebase.auth();

  const signupForm = document.getElementById("signupForm");
  const loginForm = document.getElementById("loginForm");

  // ----------------------
  // SIGNUP
  // ----------------------
  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const name = document.getElementById("name").value;
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;
      const rePassword = document.getElementById("re_password").value;

      if (password !== rePassword) {
        alert("Passwords do not match.");
        return;
      }

      try {
        // Create user
        const userCredential = await auth.createUserWithEmailAndPassword(email, password);
        const user = userCredential.user;

        // Update profile with name
        await user.updateProfile({ displayName: name });

        // (Optional) Save extra info in your database here

        alert("Account created successfully!");
        window.location.href = "/login"; // Redirect to login
      } catch (error) {
        alert("Error: " + error.message);
      }
    });
  }

  // ----------------------
  // LOGIN
  // ----------------------
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const email = document.getElementById("username").value;
      const password = document.getElementById("login_password").value;

      try {
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        const user = userCredential.user;

        // Get ID token to send to Flask
        const token = await user.getIdToken();

        // Send token to backend for session handling
        const res = await fetch("/verify_token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token })
        });

        if (res.ok) {
          window.location.href = "/dashboard";
        } else {
          alert("Login failed at backend verification.");
        }
      } catch (error) {
        alert("Login failed: " + error.message);
      }
    });
  }
});
