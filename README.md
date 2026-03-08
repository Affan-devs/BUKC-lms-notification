#  Bahria University LMS Assignment Notifier

Automatic email notifications for new assignments and upcoming deadlines.

##  Features

- 🔔 Email alerts for new assignments
- ⚠️ Deadline reminders (assignments due within 24 hours)
- ☁️ Runs automatically in the cloud via GitHub Actions
- 🆓 Completely free

---

## 🚀 Setup Instructions

### 1. Fork This Repository
Click the **Fork** button at the top right of this page.
And delete all the table data form assignments_report.csv

### 2. Get Gmail App Password
1. Go to https://myaccount.google.com/apppasswords
2. Enable 2-Factor Authentication (if not enabled)
3. Create an App Password for "Mail"
4. Copy the 16-character password

### 3. Find Your Course IDs
1. Login to [LMS](https://lms.bahria.edu.pk)
2. Go to **Assignments** page
3. **Right-click** on the course dropdown → **Inspect** (or press F12)
4. Look for lines like this:
   ```html
   <option value="MTQ3Nzgx">OOPS</option>
   ```
5. Copy the **value** (e.g., `MTQ3Nzgx`)
6. Repeat for all your courses

### 4. Add GitHub Secrets
Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 7 secrets:

| Name | Value | Example |
|------|-------|---------|
| `ENROLLMENT` | Your enrollment number | `02-239252-` |
| `PASSWORD` | Your LMS password | `your_password` |
| `INSTITUTE` | Your campus | `Karachi Campus` |
| `EMAIL_SENDER` | Your Gmail | `you@gmail.com` |
| `EMAIL_PASSWORD` | App Password from Step 2 | `abcd efgh ijkl mnop` |
| `EMAIL_RECEIVER` | Where to receive emails | `you@gmail.com` |
| `COURSE_VALUES` | Course IDs (comma-separated) | `MTQ3Nzgx,MTQ3Nzgz,MTQ3Nzg1` |

**Important:** 
- `COURSE_VALUES` must be comma-separated with **NO SPACES**
- Use the **App Password**, not your regular Gmail password

### 5. Enable GitHub Actions
1. Go to **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. Click **Run workflow** to test

---

## ⚙️ Configuration

### Change Schedule Upto you
Edit `.github/workflows/lms_checker.yml` line 5:

**change upto your requirment (default):**
```yaml
- cron: '0 3,9,15 * * *'  # 8 AM, 2 PM, 8 PM Pakistan time
```

### You can Change Deadline Alert Time
By default, you get alerts **12 hours** before deadline.

**on line 38 DEADLINE_WARNING_HOURS = 12**, edit `lms_automation_github.py` :


## 📧 Email Notifications

You'll receive **two types** of emails:

1. **🆕 New Assignment** - When new assignments are posted
2. **⚠️ Urgent Deadline** - When assignments are due within 24 hours

---

---

## 📁 Files

- `lms_automation_github.py` - Main script
- `.github/workflows/lms_checker.yml` - GitHub Actions workflow
- `requirements.txt` - Python dependencies
- `assignments_report.csv` - Auto-generated (tracks assignments)

---

**Made for Bahria University Students** 
If you found this helpful, please ⭐ star the repository!
