// File: netlify/functions/forgot-password.js
// Sends actual password with strict rate limiting

const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');

// --- INSECURE: Storing/Sending passwords in plain text ---
// This is highly discouraged for production. Use hashed passwords and reset tokens.
// --- END INSECURE WARNING ---

// --- RATE LIMITING CONFIGURATION ---
const RATE_LIMIT_USER_PER_DAY = 2;
const RATE_LIMIT_MIN_INTERVAL_HOURS = 4;
const RATE_LIMIT_GLOBAL_PER_DAY = 300;
const RATE_WINDOW_MS = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

// File to store rate limit data (ephemeral on Netlify)
const RATE_LIMIT_FILE = path.join('/tmp', 'nirobo_password_recovery_rates.json');

// --- HELPER FUNCTIONS FOR RATE LIMITING ---
function loadRateLimits() {
  try {
    if (fs.existsSync(RATE_LIMIT_FILE)) {
      const data = fs.readFileSync(RATE_LIMIT_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error("Error loading rate limits:", err.message);
  }
  // Return default structure if file doesn't exist or is corrupted
  return { users: {}, global: [] };
}

function saveRateLimits(rateData) {
  try {
    fs.writeFileSync(RATE_LIMIT_FILE, JSON.stringify(rateData, null, 2));
  } catch (err) {
    console.error("Error saving rate limits:", err.message);
    // Non-fatal, but means limits won't persist between function invocations reliably
  }
}

function isWithinRateLimit(email, rateData) {
  const now = Date.now();
  
  // 1. Check Global Limit
  const recentGlobalRequests = rateData.global.filter(timestamp => (now - timestamp) < RATE_WINDOW_MS);
  if (recentGlobalRequests.length >= RATE_LIMIT_GLOBAL_PER_DAY) {
    return { allowed: false, reason: 'global_limit' };
  }

  // 2. Check Per-User Limit
  const userRequests = rateData.users[email] || [];
  const recentUserRequests = userRequests.filter(timestamp => (now - timestamp) < RATE_WINDOW_MS);
  if (recentUserRequests.length >= RATE_LIMIT_USER_PER_DAY) {
    return { allowed: false, reason: 'user_limit' };
  }

  // 3. Check Minimum Interval
  if (recentUserRequests.length > 0) {
    const lastRequestTime = Math.max(...recentUserRequests);
    const timeSinceLastRequest = now - lastRequestTime;
    const minIntervalMs = RATE_LIMIT_MIN_INTERVAL_HOURS * 60 * 60 * 1000;
    if (timeSinceLastRequest < minIntervalMs) {
      const waitHours = Math.ceil((minIntervalMs - timeSinceLastRequest) / (1000 * 60 * 60));
      return { allowed: false, reason: 'interval', waitHours };
    }
  }

  // If all checks pass
  return { allowed: true };
}

function recordRequest(email, rateData) {
  const now = Date.now();
  
  // Record for user
  if (!rateData.users[email]) {
    rateData.users[email] = [];
  }
  rateData.users[email].push(now);
  
  // Record globally
  rateData.global.push(now);
  
  // Prune old timestamps to keep file size manageable
  for (const user_email in rateData.users) {
    rateData.users[user_email] = rateData.users[user_email].filter(ts => (now - ts) < RATE_WINDOW_MS);
  }
  rateData.global = rateData.global.filter(ts => (now - ts) < RATE_WINDOW_MS);
  
  saveRateLimits(rateData);
}

// --- MAIN HANDLER ---
exports.handler = async (event, context) => {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method Not Allowed' })
    };
  }

  try {
    // 1. Parse request body
    const { email } = JSON.parse(event.body);

    if (!email) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Email is required' })
      };
    }

    // 2. Load current rate limit data
    let rateData = loadRateLimits();

    // 3. Check rate limits
    const rateCheck = isWithinRateLimit(email, rateData);
    if (!rateCheck.allowed) {
      let errorMessage = '';
      switch (rateCheck.reason) {
        case 'global_limit':
          errorMessage = 'Daily email limit reached. Please try again tomorrow.';
          break;
        case 'user_limit':
          errorMessage = `You have reached the limit of ${RATE_LIMIT_USER_PER_DAY} password recovery requests per day. Please try again tomorrow.`;
          break;
        case 'interval':
          errorMessage = `Please wait at least ${RATE_LIMIT_MIN_INTERVAL_HOURS} hours between requests. You can try again in approximately ${rateCheck.waitHours} hours.`;
          break;
        default:
          errorMessage = 'Rate limit exceeded.';
      }
      return {
        statusCode: 429, // Too Many Requests
        body: JSON.stringify({ error: errorMessage })
      };
    }

    // 4. (Conceptual) Find user in database and get password
    // In a real app, you would query your user database here.
    // For this prototype, we'll simulate finding a user.
    // *** IMPORTANT: This is insecure. Passwords should be hashed. ***
    const users = [
      // Example user data - replace with real database query
      { email: "test@example.com", password: "mySecretPass123" },
      { email: "user@nirobo.net", password: "anotherPass456" }
      // Add more test users if needed
    ];
    const user = users.find(u => u.email === email);

    if (!user) {
      return {
        statusCode: 404,
        body: JSON.stringify({ error: 'No account found with that email address.' })
      };
    }

    // 5. Record this successful request for rate limiting
    recordRequest(email, rateData);

    // 6. Prepare email content with the ACTUAL PASSWORD (INSECURE!)
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
                .password-box { background: rgba(212, 0, 0, 0.2); padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }
                .password { font-size: 1.5rem; font-weight: bold; color: #ff9999; }
                .warning { background: rgba(255, 153, 0, 0.2); padding: 15px; border-radius: 8px; margin-top: 20px; }
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
                <p class="password">${user.password}</p> <!-- INSECURE!!! -->
              </div>
              <div class="warning">
                <p><strong>⚠️ CRITICAL SECURITY WARNING:</strong></p>
                <p>Sending passwords in plain text via email is extremely insecure. If this email is intercepted, your account is compromised. Please change your password immediately after logging in.</p>
                <p>For better security, Nirobo recommends using a password reset link instead of sending passwords directly.</p>
              </div>
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

    // 7. Send the email via Brevo API
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

    // 8. Success response
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
