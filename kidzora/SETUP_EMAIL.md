# Email Setup Guide for KidZora

## Option 1: Use Supabase Auth (Recommended)

### Step 1: Configure Supabase Email
1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Settings**
3. Under **Email Templates**, configure:
   - **Signup confirmation** template
   - **Magic link** template (optional)
   - **Recovery** template (optional)

### Step 2: Update Environment Variables
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env file
USE_SUPABASE_EMAIL=True
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

### Step 3: Supabase Email Template
Create a custom email template in Supabase that includes:
```
Hi there,

Your confirmation code is: {{ .Data.confirmation_code }}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
The KidZora Team
```

## Option 2: Use Custom SMTP

### Step 1: Update Environment Variables
```bash
# Edit .env file
USE_SUPABASE_EMAIL=False
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Step 2: Gmail Setup (if using Gmail)
1. Enable 2-factor authentication on your Gmail account
2. Go to Google Account settings → Security → App passwords
3. Generate a new app password
4. Use the app password in `MAIL_PASSWORD`

## Testing

### Test Email Sending
```python
python run.py
# Go to http://localhost:5000/auth/email-verification
# Enter your email and check if you receive the confirmation code
```

## Troubleshooting

### Supabase Email Issues
- Check Supabase project email settings
- Verify email templates are properly configured
- Check Supabase service role key permissions

### SMTP Email Issues
- Verify email credentials are correct
- Check firewall settings
- Ensure app passwords are used (not regular passwords)
- Check SMTP server and port settings

### Common Issues
- **"Email not sent"**: Check environment variables are loaded correctly
- **"Invalid credentials"**: Use app passwords for Gmail, not regular passwords
- **"Connection refused"**: Check firewall and SMTP settings

## Production Deployment

### Environment Variables
Set these in your hosting environment:
- `USE_SUPABASE_EMAIL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `MAIL_SERVER` (if using SMTP)
- `MAIL_USERNAME` (if using SMTP)
- `MAIL_PASSWORD` (if using SMTP)

### Security Notes
- Never commit `.env` file to version control
- Use app passwords for email services
- Enable 2-factor authentication on email accounts
- Use environment variables in production
