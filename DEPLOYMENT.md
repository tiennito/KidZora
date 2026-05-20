# KidZora Deployment Guide

## Pre-Deployment Checklist

### 1. ✅ Security - MANDATORY
- [x] Removed hardcoded API keys from source code
- [x] Disabled debug mode in production
- [ ] **YOU MUST REVOKE** the exposed Resend API key: `re_cGQHWAKD_C8XTsGLcpvrkE6AgoQRAvEHJ`
  - Visit: https://dashboard.resend.com/api-keys
  - Delete the old key
  - Generate a new one and save it securely
- [ ] Create a strong SECRET_KEY (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] All secrets are in `.env` file (NOT in git)

### 2. Environment Variables for Vercel
Copy `.env.vercel.example` to Vercel Project Settings:

**Required Variables:**
```
FLASK_CONFIG=production
FLASK_ENV=production
SECRET_KEY=<generate-new-secure-key>

# Supabase (CRITICAL)
SUPABASE_URL=<your-supabase-url>
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Email (Resend)
MAIL_SERVER=smtp.resend.com
MAIL_PORT=465
MAIL_USERNAME=resend
MAIL_PASSWORD=<new-resend-api-key>
MAIL_DEFAULT_SENDER=KidZora <your-email@resend.dev>

# Optional but recommended
VAPID_PRIVATE_KEY=<your-vapid-private-key>
VAPID_PUBLIC_KEY=<your-vapid-public-key>
VAPID_MAILTO=mailto:admin@kidzora.com
```

### 3. Vercel Deployment Steps

#### Via Vercel CLI:
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

#### Via GitHub (Recommended):
1. Push your code to GitHub
2. Connect repo to Vercel: https://vercel.com/new
3. Configure environment variables in Project Settings
4. Deploy

### 4. Database Setup
Ensure Supabase database is fully configured:
- [ ] All migration scripts have run
- [ ] Tables are created with proper schema
- [ ] Row-level security (RLS) is configured
- [ ] Service role key is secure and only used server-side

### 5. Post-Deployment Tests
- [ ] Health check: `GET /` returns 200
- [ ] Database connectivity verified
- [ ] Email sending works
- [ ] All API endpoints respond correctly
- [ ] Static assets load properly
- [ ] SSL certificate is valid

### 6. Monitoring & Maintenance
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Monitor logs in Vercel dashboard
- [ ] Check Supabase database usage/quotas
- [ ] Regular backups configured
- [ ] Keep dependencies updated

## Project Structure for Deployment

```
kidzora/
├── api/index.py              # Vercel serverless entry point
├── kidzora/
│   ├── run.py               # Flask app initialization
│   ├── config.py            # Configuration (environment-aware)
│   ├── requirements.txt      # Python dependencies
│   └── app/
│       ├── __init__.py
│       ├── routes/          # API and page routes
│       └── static/          # Static files
├── .env.vercel.example      # Environment template
├── vercel.json              # Vercel configuration
└── .gitignore               # Prevents secrets from git
```

## Important Notes

⚠️ **BEFORE DEPLOYING:**
1. Revoke the exposed Resend API key immediately
2. Generate all new secrets (SECRET_KEY, new MAIL_PASSWORD)
3. Test locally with production config: `FLASK_CONFIG=production FLASK_ENV=production python kidzora/run.py`
4. Ensure all required environment variables are set in Vercel

✅ **What's Ready:**
- Vercel configuration (vercel.json)
- Flask app with environment-aware config
- Security fixes applied
- Python dependencies listed

## Troubleshooting

**App crashes with "SUPABASE_URL not found":**
- Verify environment variables are set in Vercel Project Settings
- Check Settings > Environment Variables

**Database connection errors:**
- Verify Supabase credentials are correct
- Check network access in Supabase settings

**Email not sending:**
- New Resend API key set correctly
- MAIL_PASSWORD is not empty
- Email configuration variables match Vercel settings

**Static files not loading:**
- Ensure vercel.json outputDirectory is correct (currently ".")
- Check app/static/ folder exists
