// File: netlify/functions/forgot-password.js
// Sends actual password (INSECURE) with rate limiting

const fetch = require('node-fetch');

// --- INSECURE: Storing passwords in plain text ---
// In a real app, passwords should be HASHED and NEVER sent via email.
// This is for demonstration only based on your request.
// --- END INSECURE WARNING ---

exports.handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method Not Allowed' })
    };
  }

  try {
    const { email } = JSON.parse(event.body);

    if (!email) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Email is required' })
      };
    }

    // --- RATE LIMITING LOGIC ---
    const now = Date.now();
    const RATE_LIMIT_WINDOW_MS = 24 * 60 * 60 * 1000; // 24 hours
    const MIN_REQUEST_INTERVAL_MS = 4 * 60 * 60 * 1000; // 4 hours

    // 1. Get rate limit data from Netlify Function's temporary file system
    // Note: This is a SIMULATION. In production, use a proper database.
    // For this demo, we'll use a simple file to track requests.
    // This requires enabling Netlify's "Functions" file system access.
    const fs = require('fs');
    const path = require('path');
    const RATE_LIMIT_FILE_PATH = path.join('/tmp', 'nirobo_rate_limits.json'); // Netlify's temp dir

    let rateLimits = {};
    try {
        // Try to read existing rate limit data
        if (fs.existsSync(RATE_FILE_PATH)) {
            const data = fs.readFileSync(RATE_FILE_PATH, 'utf8');
            rateLimits = JSON.parse(data);
        }
    } catch (err) {
        console.warn("Could not read rate limit file, starting fresh:", err.message);
        rateLimits = {};
    }

    // 2. Check global daily limit (300 emails)
    const recentGlobalRequests = Object.values(rateLimits).flat().filter(ts => (now - ts) < RATE_LIMIT_WINDOW_MS);
    if (recentGlobalRequests.length >= 300) {
        return {
            statusCode: 429, // Too Many Requests
            body: JSON.stringify({ error: 'Daily email limit reached. Please try again tomorrow.' })
        };
    }

    // 3. Check per-user limit (2 requests per day)
    const userRequests = rateLimits[email] || [];
    const recentUserRequests = userRequests.filter(ts => (now - ts) < RATE_LIMIT_WINDOW_MS);
    if (recentUserRequests.length >= 2) {
        return {
            statusCode: 429,
            body: JSON.stringify({ error: 'You have reached the limit of 2 password recovery requests per day. Please try again tomorrow.' })
        };
    }

    // 4. Check minimum interval (4 hours)
    if (recentUserRequests.length > 0) {
        const lastRequestTime = Math.max(...recentUserRequests);
        if ((now - lastRequestTime) < MIN_REQUEST_INTERVAL_MS) {
            const waitHours = Math.ceil((MIN_REQUEST_INTERVAL_MS - (now - lastRequestTime)) / (1000 * 60 * 60));
            return {
                statusCode: 429,
                body: JSON.stringify({ error: `Please wait at least 4 hours between requests. You can try again in approximately ${waitHours} hours.` })
            };
        }
    }
    // --- END RATE LIMITING LOGIC ---

    // --- FIND USER & SEND PASSWORD ---
    // Conceptual: Load user data (in a real app, from a database)
    // For this demo, we'll simulate loading from a file or database
    // Since we don't have a real database, we'll assume passwords are stored in plain text
    // This is a MAJOR SECURITY FLAW. DO NOT DO THIS IN PRODUCTION.
    let userData = [];
    try {
        // Simulate loading user data
        // In a real backend, you'd query your user database
        // For demo, let's assume we have a way to access user data
        // This is a placeholder. You need a real user database.
        const userResponse = await fetch('https://your-site.netlify.app/data/users.json'); // Hypothetical user data file
        if (userResponse.ok) {
            userData = await userResponse.json();
        } else {
            // Fallback: Check localStorage (conceptual, not possible directly in Netlify Function)
            // This part is impossible in a Netlify Function without a database.
            // We'll simulate finding the user.
            userData = [
                { email: "test@example.com", password: "plaintext_password_123" },
                { email: "user@nirobo.net", password: "another_plaintext_pass" }
                // Add more simulated users if needed for testing
            ];
        }
    } catch (err) {
        console.error("Error loading user data:", err);
        userData = [
             { email: "test@example.com", password: "plaintext_password_123" },
             { email: "user@nirobo.net", password: "another_plaintext_pass" }
        ];
    }

    const user = userData.find(u => u.email === email);

    if (!user) {
      return {
        statusCode: 404,
        body: JSON.stringify({ error: 'No account found with that email address.' })
      };
    }

    // --- PREPARE EMAIL WITH ACTUAL PASSWORD (INSECURE) ---
    const emailData = {
      sender: { email: "noreply@nirobo.netlify.app", name: "Nirobo Search" },
      to: [{ email: email }],
      subject: "[Nirobo] Your Password Recovery Request",
      htmlContent: `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Password Recovery</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #0a1f0a; color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a1a; border-radius: 10px; }
                .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #333; }
                .logo { font-size: 2rem; color: #d40000; }
                .content { padding: 20px 0; }
                .password-box { background: rgba(212, 0, 0, 0.2); padding: 15px; border-radius: 8px; margin: 20px 0; }
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
              <h2>Password Recovery Request</h2>
              <p>Hello,</p>
              <p>You have requested to recover your password for your Nirobo account.</p>
              <div class="password-box">
                <p><strong>Your Password is:</strong></p>
                <p style="font-size: 1.5rem; font-weight: bold; color: #ff9999;">${user.password}</p> <!-- INSECURE!!! -->
              </div>
              <p><strong>⚠️ CRITICAL SECURITY WARNING:</strong></p>
              <p>Sending passwords in plain text via email is extremely insecure. If this email is intercepted, your account is compromised. Please change your password immediately after logging in.</p>
              <p>For better security, Nirobo recommends using a password reset link instead of sending passwords directly.</p>
              <a href="https://your-site.netlify.app/signup.html" style="display: inline-block; padding: 12px 24px; background: #d40000; color: white; text-decoration: none; border-radius: 30px; font-weight: bold; margin-top: 20px;">Log In & Change Password</a>
            </div>
            <div class="footer">
              <p>Made in Bangladesh 🇧🇩 | Curated by Nirobo</p>
              <p>Honoring the Language Movement and the Silent Legacy of Justice</p>
              <p>Crafted by KH. AL SHAIF — for truth, clarity, and cultural dignity</p>
            </div>
          </div>
        </body>
        </html>
      `
    };

    // --- SEND EMAIL VIA BREVO ---
    const response = await fetch('https://api.brevo.com/v3.1/smtp/email', {
      method: 'POST',
      headers: {
        'accept': 'application/json',
        'api-key': 'YOUR_REAL_BREVO_API_KEY_HERE', // <-- REPLACE WITH YOUR ACTUAL KEY
        'content-type': 'application/json'
      },
      body: JSON.stringify(emailData)
    });

    const data = await response.json();

    if (!response.ok) {
      console.error("Brevo API Error:", data);
      return {
        statusCode: response.status || 500,
        body: JSON.stringify({ error: `Failed to send email: ${data.message || 'Unknown error'}` })
      };
    }

    // --- UPDATE RATE LIMITS ---
    // Record this request
    if (!rateLimits[email]) {
        rateLimits[email] = [];
    }
    rateLimits[email].push(now);
    // Keep only timestamps within the window
    rateLimits[email] = rateLimits[email].filter(ts => (now - ts) < RATE_LIMIT_WINDOW_MS);
    // Update global requests list
    // (This simplistic approach might not be perfectly accurate for global count,
    // but it's a reasonable simulation for a prototype)
    // A real DB would have a better way to track this.

    try {
        // Save updated rate limits
        fs.writeFileSync(RATE_FILE_PATH, JSON.stringify(rateLimits, null, 2));
    } catch (err) {
        console.error("Failed to write rate limit file:", err);
        // Non-fatal error, email was sent successfully
    }
    // --- END UPDATE RATE LIMITS ---

    return {
      statusCode: 200,
      body: JSON.stringify({ message: `Your password has been sent to ${email}. Please check your inbox/spam.` })
    };

  } catch (error) {
    console.error("Function error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal Server Error' })
    };
  }
};
