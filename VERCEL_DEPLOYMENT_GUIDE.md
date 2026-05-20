# Complete Vercel Deployment Instructions

## Step 1: Security - Immediate Actions Required

### ⚠️ REVOKE EXPOSED API KEY (DO THIS FIRST)
1. Visit https://dashboard.resend.com/api-keys
2. Find and delete the old API key: `re_cGQHWAKD_C8XTsGLcpvrkE6AgoQRAvEHJ`
3. **Generate a NEW Resend API key** - save it securely

### Generate Production Secrets
Open PowerShell and run:
```powershell
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Save output - you'll need this for Vercel
```

## Step 2: Setup Local Environment for Testing

### 2a. Create `.env` file locally (NOT committed to git)
```bash
# Copy template
copy .env.vercel.example .env
```

### 2b. Edit `.env` with YOUR values:
```
FLASK_CONFIG=production
FLASK_ENV=production
SECRET_KEY=<your-generated-key-from-step-1>

SUPABASE_URL=<from-supabase-dashboard>
SUPABASE_ANON_KEY=<from-supabase-dashboard>
SUPABASE_SERVICE_ROLE_KEY=<from-supabase-dashboard>

MAIL_PASSWORD=<your-new-resend-api-key>
MAIL_DEFAULT_SENDER=KidZora <your-email@resend.dev>

VAPID_PRIVATE_KEY=<if-you-have-it>
VAPID_PUBLIC_KEY=<if-you-have-it>
```

### 2c. Test locally (PowerShell)
```powershell
.\test_production.ps1

# Then in same terminal:
python kidzora/run.py

# Visit http://localhost:5000
```

If all works → proceed to Step 3

## Step 3: Push Code to GitHub

```powershell
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

**Verify these are NOT in git:**
- .env file
- .env.local
- API keys anywhere

## Step 4: Deploy to Vercel

### Option A: Using Vercel CLI (Recommended)
```powershell
npm install -g vercel

# Deploy
vercel --prod
```

### Option B: Connect GitHub to Vercel
1. Go to https://vercel.com/new
2. Select "Import Git Repository"
3. Choose your GitHub repo
4. Continue to next step

## Step 5: Configure Environment Variables in Vercel

After creating the project on Vercel:

1. Go to: **Project Settings → Environment Variables**
2. Add each variable with correct values:

| Variable | Value | Environment |
|----------|-------|-------------|
| FLASK_CONFIG | production | Production |
| FLASK_ENV | production | Production |
| SECRET_KEY | Your generated key | Production |
| SUPABASE_URL | Your Supabase URL | Production |
| SUPABASE_ANON_KEY | Your anon key | Production |
| SUPABASE_SERVICE_ROLE_KEY | Your service role key | Production |
| MAIL_PASSWORD | Your new Resend API key | Production |
| MAIL_DEFAULT_SENDER | KidZora <your-email@resend.dev> | Production |
| MAIL_SERVER | smtp.resend.com | Production |
| MAIL_PORT | 465 | Production |
| MAIL_USERNAME | resend | Production |

**For optional Web Push:**
| VAPID_PRIVATE_KEY | Your key | Production |
| VAPID_PUBLIC_KEY | Your key | Production |

3. Click "Deploy" or let it auto-deploy from GitHub

## Step 6: Test Deployment

After deployment completes:

1. Visit your Vercel domain (e.g., `your-app.vercel.app`)
2. Check that pages load
3. Test a database query
4. Verify email sending works
5. Check Vercel logs for errors: **Deployments → Logs**

## Step 7: Monitor & Maintain

### Check Logs
- Vercel Dashboard → Deployments → Function Logs

### Monitor Errors
- Vercel Dashboard → Monitoring

### Common Issues & Fixes

**"SUPABASE_URL is not defined"**
- ✅ Check Vercel Project Settings → Environment Variables
- ✅ Redeploy after adding variables

**"Connection refused" to database**
- ✅ Verify Supabase keys are correct
- ✅ Check Supabase project is running

**Email not sending**
- ✅ New Resend API key is set
- ✅ MAIL_PASSWORD is not empty in Vercel env vars

**500 errors in logs**
- ✅ Check Vercel Logs for detailed error
- ✅ Ensure all env vars are set
- ✅ Test locally first

## Final Checklist

Before considering deployment complete:

- [ ] Exposed Resend API key revoked
- [ ] New Resend API key generated and set
- [ ] SECRET_KEY generated and set in Vercel
- [ ] All environment variables configured in Vercel
- [ ] Code pushed to GitHub
- [ ] App deployed to Vercel successfully
- [ ] App loads without errors
- [ ] Database connectivity verified
- [ ] Email sending verified
- [ ] No secrets in .git history

---

**Need Help?**
- Vercel Docs: https://vercel.com/docs/frameworks/flask
- Supabase Docs: https://supabase.com/docs
- Flask Docs: https://flask.palletsprojects.com/
