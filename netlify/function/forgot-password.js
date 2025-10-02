// File: netlify/functions/forgot-password.js
// This script runs on Netlify's servers when someone clicks "Forgot Password"

// Netlify Functions come with 'node-fetch' built-in for making HTTP requests
const fetch = require('node-fetch');

exports.handler = async (event, context) => {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405, // Method Not Allowed
      body: JSON.stringify({ error: 'Method Not Allowed' })
    };
  }

  try {
    // 1. Get the email address sent from the frontend (signup.html)
    const requestData = JSON.parse(event.body);
    const { email } = requestData;

    if (!email) {
      return {
        statusCode: 400, // Bad Request
        body: JSON.stringify({ error: 'Email is required' })
      };
    }

    // 2. (Conceptual) Check if the email exists in your user database.
    //    For this example, we'll assume the email is valid.
    //    In a real app, you would connect to your database (e.g., Firebase, MongoDB) here.
    //    This is a placeholder. You need to implement real user lookup.
    const userExists = true; // <-- Replace with real database check

    if (!userExists) {
      return {
        statusCode: 404, // Not Found
        body: JSON.stringify({ error: 'No account found with that email address.' })
      };
    }

    // 3. Prepare the email content to send via Brevo
    const emailData = {
      sender: { email: "noreply@nirobo.netlify.app", name: "Nirobo Search" }, // Update if you have a verified sender
      to: [{ email: email }], // Send to the user's email
      subject: "[Nirobo] Password Reset Request",
      htmlContent: `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Password Reset</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #0a1f0a; color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a1a; border-radius: 10px; }
                .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #333; }
                .logo { font-size: 2rem; color: #d40000; }
                .content { padding: 20px 0; }
                .button { display: inline-block; padding: 12px 24px; background-color: #d40000; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }
                .footer { text-align: center; padding: 20px 0; border-top: 1px solid #333; font-size: 0.8rem; color: #888; }
            </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="logo">NIROBO</div>
              <p>"Intelligent URL Discovery Powered by AI"</p>
            </div>
            <div class="content">
              <h2>Password Reset Request</h2>
              <p>Hello,</p>
              <p>You have requested to reset your password for your Nirobo account.</p>
              <p><strong>⚠️ NOTE: This is a simulated request for demonstration.</strong></p>
              <p>In a real application, a secure reset link would be sent here.</p>
              <p>For now, please contact the admin at <a href="mailto:infinitealphas0602@outlook.com" style="color: #ff9999;">infinitealphas0602@outlook.com</a> to reset your password.</p>
              <a href="mailto:infinitealphas0602@outlook.com?subject=[Nirobo Password Reset]&body=Please reset my password for ${email}" class="button">Reset Password via Email</a>
            </div>
            <div class="footer">
              <p>Made in Bangladesh 🇧🇩 | Curated by Nirobo</p>
              <p>Honoring the Language Movement and the Silent Legacy of Justice</p>
            </div>
          </div>
        </body>
        </html>
      `
    };

    // 4. Send the request to Brevo's SMTP API
    //    IMPORTANT: The API key is safely stored HERE on the server, not in signup.html
    const response = await fetch('https://api.brevo.com/v3.1/smtp/email', {
      method: 'POST',
      headers: {
        'accept': 'application/json',
        'api-key': 'eyJhcGlfa2V5IjoieGtleXNpYi1kZjk5ZjM5Y2I4ZWQ1Njk1NzBlYTYyM2NiNmExZTU3Mjc5NmU4YWUxZjI1NWQ2ZjQxZDBhNGY3ZDVmODU5ZDcyLXZUb1FEN3lOZ1lSaG11ZUEifQ==', // <-- PASTE YOUR ACTUAL KEY HERE
        'content-type': 'application/json'
      },
      body: JSON.stringify(emailData)
    });

    // 5. Parse the response from Brevo
    const data = await response.json();

    // 6. Check if Brevo accepted the request
    if (!response.ok) {
      console.error("Brevo API Error:", data);
      return {
        statusCode: response.status || 500,
        body: JSON.stringify({ error: `Failed to send email: ${data.message || 'Unknown error'}` })
      };
    }

    // 7. If successful, tell the frontend
    return {
      statusCode: 200, // OK
      body: JSON.stringify({ message: `Password reset instructions sent to ${email}` })
    };

  } catch (error) {
    // 8. Handle any unexpected errors
    console.error("Function error:", error);
    return {
      statusCode: 500, // Internal Server Error
      body: JSON.stringify({ error: 'Internal Server Error' })
    };
  }
};
