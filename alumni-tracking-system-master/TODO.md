# WVSU Alumni Tracking System - SAFE GitHub + Internet Deployment
# Current: Local Flask app → GitHub repo → Railway live URL
# Safety: Local files/DB unchanged. Prod copy only.

# Progress Tracker (6/8 ✅)
- [x] **Backup database** - Manual copy  
- [x] **Git init** - Manual commands  
- [x] **TODO.md** - Progress tracking  
- [x] **Procfile/runtime.txt/.gitignore/railway.json** - Production files ✅
- [x] **Gunicorn installed** - Production server ready
- [ ] **GitHub repo + push**
- [ ] **Railway deploy** → LIVE URL! 🎉

### 🔒 SAFETY FIRST (Done)
- [x] **Backup database** - `instance/database.db` preserved
- [x] **Git init** - New repo (doesn't delete files)  
- [x] **TODO.md** - This file created

### 📂 GitHub Setup (Next)
- [ ] Commit all files  
- [ ] Create GitHub repo `wvsu-alumni-tracking`
- [ ] Push main branch

### ⚙️ Production Files (Safe - no local impact)
- [ ] Procfile (`web: gunicorn app:app`)
- [ ] runtime.txt (`python-3.12.6`)
- [ ] .gitignore (hide DB/uploads)
render.yaml (Render config)

### 🧪 Local Production Test
- [ ] `gunicorn app:app` → localhost:8000 (proves safe)

**Render Live Deploy** (render.com)
- [ ] New Railway project from GitHub
- [ ] PostgreSQL database addon  
- [ ] Set env vars (SECRET_KEY, DATABASE_URL)
- [ ] Live URL ready! (https://wvsu-alumni.railway.app)

### ✅ Post-Deploy
- [ ] Test all features live
- [ ] Migrate local data (optional)
- [ ] Custom domain (optional $5/mo)

## Quick Commands (Copy-Paste)
```
# 1. Current dir: alumni-tracking-system-master
git add . & git commit -m \"Deployment prep\" & git push
```

## Rollback (Anytime)
```
git reset --hard HEAD~1  # Undo 1 commit
git clean -fd            # Remove new files
```

**Status: READY** - Next: GitHub repo creation + safe prod files

