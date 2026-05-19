# KidZora Setup Guide

## 🚀 Quick Setup

### Step 1: Add Your Supabase Credentials

Edit the `.env` file and replace these placeholders:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key-here
```

### Step 2: Email Configuration (Already Done)

Your Resend email configuration is already set:
```bash
# Email Configuration - Using Resend
USE_SUPABASE_EMAIL=False
MAIL_SERVER=smtp.resend.com
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=resend
MAIL_PASSWORD=re_QCU3RHM1_7wYJBpWn5fEv3rJA83QhR87T
MAIL_DEFAULT_SENDER=KidZora <onboarding@resend.dev>
```

### Step 3: Run the Application

```bash
python run.py
```

### Step 4: Test Registration

1. Open: http://localhost:5000/auth/register
2. Fill in all registration fields
3. Click "Create Account"
4. Check your email for 6-digit code
5. Enter code in the modal
6. Account created successfully!

## 🔧 Where to Find Supabase Credentials

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to Settings → API
4. Copy the **Project URL** and **anon public key**
5. Paste them into your `.env` file

## 📧 Email Configuration Details

Your Resend configuration is working with:
- **Server**: smtp.resend.com:465 (SSL)
- **Username**: resend
- **Password**: re_QCU3RHM1_7wYJBpWn5fEv3rJA83QhR87T
- **Sender**: KidZora <onboarding@resend.dev>

## 🎯 Registration Flow

1. **Form Fill** → User fills complete registration
2. **Email Send** → System sends 6-digit code via Resend
3. **Code Verify** → User enters code in modal
4. **Account Create** → Account created in Supabase
5. **Login** → User can login immediately

## ✅ Ready to Go!

Once you add your Supabase credentials to the `.env` file, the complete registration system will work with:
- Email verification via Resend
- Account creation in Supabase
- Professional user experience
- Secure authentication flow
