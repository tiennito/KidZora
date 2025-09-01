document.addEventListener("DOMContentLoaded", () => {
  const auth = window.firebaseAuth;
  const { createUserWithEmailAndPassword, signInWithEmailAndPassword } = window.firebaseMethods;

  const signupForm = document.getElementById("signupForm");
  const loginForm = document.getElementById("loginForm");

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
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        alert("Account created successfully!");
        window.location.href = "/login"; // or any page
      } catch (error) {
        alert("Error: " + error.message);
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const email = document.getElementById("username").value;
      const password = document.getElementById("login_password").value;

      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        alert("Logged in successfully!");
        // Redirect to dashboard or home
        window.location.href = "/";
      } catch (error) {
        alert("Login failed: " + error.message);
      }
    });
  }
});
