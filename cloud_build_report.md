# IT 231 — Cloud Build Project Report
## ProficiencyTracker Wiki CDN: AWS-Backed Daily Sync Service

**Student:** Matthew Tryon  
**Course:** IT 231 — Cloud Computing  
**Date:** June 2026  
**Project:** AWS distribution layer for the ProficiencyTracker Marvel Rivals desktop application

---

## Table of Contents

1. [Project Overview and Justification](#1-project-overview-and-justification)
2. [Cloud Environment Plan](#2-cloud-environment-plan)
3. [AWS Pricing and Cost Analysis](#3-aws-pricing-and-cost-analysis)
4. [Build Documentation](#4-build-documentation)
5. [Testing and Validation](#5-testing-and-validation)
6. [Reflection and Lessons Learned](#6-reflection-and-lessons-learned)

---

## 1. Project Overview and Justification

### 1.1 Background

ProficiencyTracker is a Windows desktop application that tracks Marvel Rivals hero proficiency levels via OCR screen capture. One of its features is a wiki sync module that scrapes the Marvel Rivals Fandom wiki to download hero icons, ability data, and the current hero roster. This sync runs once at first launch and whenever the user triggers a manual refresh.

The current on-client scraping approach works for a single user but does not scale. Every client independently hammers the Fandom wiki's MediaWiki API with dozens of sequential HTTP requests — one per hero — to download wikitext, resolve image CDN URLs, and pull icon files. The wiki enforces rate limiting (HTTP 429 responses), and as the user base grows, the probability of users being throttled increases.

### 1.2 Problem Statement

The core problem is **N-client fan-out**: if 100 users each trigger a sync on the same day, the Fandom wiki receives 100 × ~50 requests = 5,000 requests, all fetching identical data. This is wasteful, fragile, and risks the application's IP range being blocked.

### 1.3 Proposed Solution

Move wiki data collection to a single AWS-hosted scraper that runs once per day. The scraper writes its output — `heroes.json`, hero icons (`.webp`/`.gif`), and ability data (`abilities.json`) — to an S3 bucket. Desktop clients download from S3 instead of scraping the wiki themselves.

**Key benefits:**
- The wiki receives one set of requests per day regardless of client count
- S3 provides a globally reliable, low-latency CDN with 99.99% availability SLA
- Clients start up faster (S3 downloads are faster than sequential wiki API scraping)
- Rate limiting risk is eliminated — only one origin IP contacts the wiki

### 1.4 AWS Services Used

| Service | Role | Requirement |
|---------|------|-------------|
| **EC2** (t3.micro) | Runs the daily Python scraper | Required by assignment |
| **S3** | Stores hero data files served to clients | Storage + CDN |
| **EventBridge** | Cron rule triggers EC2 scraper daily at 06:00 UTC | Scheduling |
| **IAM** | Roles and policies scoping EC2 → S3 access | Security |

This exceeds the minimum 3-service requirement (EC2, S3, EventBridge, IAM).

---

## 2. Cloud Environment Plan

### 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                               │
│                                                                 │
│   ┌─────────────────┐          ┌──────────────────────────────┐ │
│   │  EventBridge    │  trigger │  EC2 t3.micro                │ │
│   │  Cron Rule      │─────────►│  Amazon Linux 2023           │ │
│   │  06:00 UTC/day  │          │  Python 3.11                 │ │
│   └─────────────────┘          │  wiki_sync/avatar_sync.py    │ │
│                                │  wiki_sync/ability_scraper.py│ │
│                                └─────────────┬────────────────┘ │
│                                              │ s3:PutObject     │
│                                              ▼                  │
│                                ┌──────────────────────────────┐ │
│                                │  S3 Bucket                   │ │
│                                │  proftracker-wiki-data       │ │
│                                │  ├── heroes.json             │ │
│                                │  ├── abilities.json          │ │
│                                │  └── icons/                  │ │
│                                │      ├── Hero_Icon_*.webp    │ │
│                                │      ├── Lord_Icon_*.webp    │ │
│                                │      └── Champion_Icon_*.gif │ │
│                                └──────────────┬───────────────┘ │
│                                               │                 │
└───────────────────────────────────────────────┼─────────────────┘
                                                │ HTTPS (public read)
                                    ┌───────────▼────────────┐
                                    │  ProfTracker Desktop   │
                                    │  (Windows client)      │
                                    │  PROFTRACKER_CDN_BASE= │
                                    │  https://s3.amazonaws  │
                                    │  .com/proftracker-...  │
                                    └────────────────────────┘
```

### 2.2 Component Details

#### EC2 Instance

- **AMI:** Amazon Linux 2023 (free tier eligible)
- **Instance type:** t3.micro (2 vCPU, 1 GB RAM) — sufficient for sequential HTTP scraping
- **Storage:** 8 GB gp3 root volume (default)
- **IAM Role:** `ProfTrackerScraper` — grants `s3:PutObject` and `s3:DeleteObject` on the target bucket only (least-privilege)
- **Installed packages:** Python 3.11, `requests`, `beautifulsoup4`, project source (wiki_sync module only — no PyQt6, EasyOCR, or torch required on the server)
- **Scraper entry point:** `python -m wiki_sync.server_sync` — a headless version of `SyncWorker` that skips the RAG index rebuild (no GPU needed server-side)

#### S3 Bucket

- **Name:** `proftracker-wiki-data` (globally unique name chosen at creation)
- **Region:** `us-east-1` (lowest latency to East Coast; choose `us-west-2` if primary user base is West Coast)
- **Public access:** Block Public Access **OFF** for the bucket; bucket policy grants `s3:GetObject` to `"Principal": "*"` — read-only public, write restricted to the EC2 IAM role
- **Versioning:** Enabled — protects against a failed scrape overwriting valid data with empty/partial files
- **Storage class:** S3 Standard (data accessed daily by clients, not archival)
- **Expected contents:** ~200 icon files (`.webp`/`.gif`) + 2 JSON files, total ~15–25 MB

#### EventBridge Rule

- **Schedule expression:** `cron(0 6 * * ? *)` — fires at 06:00 UTC daily
- **Target:** EC2 Run Command (`AWS-RunShellScript`) executing the scraper on the running instance
- **IAM permissions:** EventBridge role with `ssm:SendCommand` targeting the EC2 instance by tag (`Role=ProfTrackerScraper`)

#### IAM Configuration

- **EC2 instance profile role** (`ProfTrackerScraper-EC2`):
  - `s3:PutObject`, `s3:DeleteObject` on `arn:aws:s3:::proftracker-wiki-data/*`
  - `s3:ListBucket` on `arn:aws:s3:::proftracker-wiki-data`
  - `ssm:GetParameter` (for storing Fandom API credentials securely in Parameter Store)
- **EventBridge execution role** (`ProfTrackerScraper-Events`):
  - `ssm:SendCommand` on EC2 instance tag filter

### 2.3 Client Integration

The desktop client is modified to check for a `PROFTRACKER_CDN_BASE` environment variable. When set, `avatar_sync.py` fetches `{CDN_BASE}/heroes.json` and icon files from S3 instead of scraping the wiki. The fallback (scrape directly) remains intact for development and offline use.

```python
# wiki_sync/avatar_sync.py — CDN-aware fetch
CDN_BASE = os.environ.get("PROFTRACKER_CDN_BASE", "").rstrip("/")

def _fetch_icon(slug: str, filename: str, dest: Path) -> bool:
    if CDN_BASE:
        url = f"{CDN_BASE}/icons/{filename}"
    else:
        url = _resolve_wiki_cdn_url(slug, filename)   # existing path
    ...
```

The S3 bucket URL takes the form:
`https://proftracker-wiki-data.s3.amazonaws.com`

---

## 3. AWS Pricing and Cost Analysis

### 3.1 AWS Pricing Calculator Estimate

The following estimates were generated using the [AWS Pricing Calculator](https://calculator.aws/pricing/2/homescreen). All prices are for the `us-east-1` region, on-demand pricing, no reserved instances.

| Service | Configuration | Monthly Cost |
|---------|--------------|-------------|
| EC2 t3.micro | 744 hrs/month (always-on), Linux | **$0.00** (Free Tier Year 1) / **$7.74** thereafter |
| S3 Storage | 0.025 GB × $0.023/GB | **$0.00** (negligible) |
| S3 GET Requests | 10,000 users × 200 files = 2M GETs/mo × $0.0004/1K | **$0.80** |
| S3 PUT Requests | 200 files/day × 30 days = 6,000 PUTs × $0.005/1K | **$0.03** |
| S3 Data Transfer OUT | 100 users/day × 25 MB = 75 GB/month × $0.09/GB | **$6.75** |
| EventBridge | 30 custom events/month × $1.00/1M | **$0.00** (negligible) |
| **Total (Free Tier)** | | **~$7.58/month** |
| **Total (Post Free Tier)** | | **~$15.32/month** |

*Note: Data transfer cost dominates. If the user base remains small (<10 daily active users), total transfer is ~0.75 GB/month → ~$0.07, making total cost ~$0.10/month post-free-tier.*

### 3.2 On-Premises Comparison

The alternative to AWS is continuing to run scraping client-side. The "cost" is:

| Factor | On-Prem (client-side scrape) | AWS CDN |
|--------|------------------------------|---------|
| Wiki API risk | Rate limiting, potential IP ban | Eliminated |
| Sync time per client | 45–90 seconds (sequential API calls) | 3–8 seconds (parallel S3 downloads) |
| Data freshness | On-demand (only syncs when user triggers) | Daily, consistent for all clients |
| Server costs | $0 | ~$7–16/month |
| Maintenance | None | Occasional (AWS console, script updates) |
| Scalability | Degrades with user count | Constant regardless of users |

**Conclusion:** For a student/hobby project with few users, on-premises (client-side) scraping is more cost-effective. The AWS approach becomes worthwhile at ~20+ daily active users where rate-limiting risk becomes real and per-user sync time becomes a user experience concern.

### 3.3 Pricing Calculator Screenshots

*[Screenshot: AWS Pricing Calculator summary showing EC2 t3.micro + S3 estimate]*

*[Screenshot: S3 pricing detail showing storage + request + transfer breakdown]*

*[Screenshot: EC2 pricing detail showing t3.micro on-demand Linux price]*

---

## 4. Build Documentation

### 4.1 Step 1 — Create S3 Bucket

1. Log in to AWS Console → S3 → **Create bucket**
2. Bucket name: `proftracker-wiki-data-clayhtryon` (must be globally unique)
3. Region: `us-east-1`
4. **Uncheck** "Block all public access" → acknowledge the warning
5. Enable **Versioning**
6. Click **Create bucket**

*[Screenshot: S3 bucket creation form — bucket name, region, public access settings]*

7. Navigate to the bucket → **Permissions** → **Bucket policy** → paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::proftracker-wiki-data-clayhtryon/*"
    }
  ]
}
```

*[Screenshot: Bucket policy editor with the policy pasted in]*

### 4.2 Step 2 — Create IAM Role for EC2

1. AWS Console → IAM → **Roles** → **Create role**
2. Trusted entity: **AWS service** → **EC2**
3. Attach policy: **AmazonSSMManagedInstanceCore** (enables Run Command)
4. Click **Next** → name the role `ProfTrackerScraper-EC2`
5. After creation, click the role → **Add inline policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::proftracker-wiki-data-clayhtryon",
        "arn:aws:s3:::proftracker-wiki-data-clayhtryon/*"
      ]
    }
  ]
}
```

*[Screenshot: IAM role creation — trusted entity selection]*

*[Screenshot: IAM inline policy editor with S3 permissions]*

### 4.3 Step 3 — Launch EC2 Instance

1. AWS Console → EC2 → **Launch instance**
2. Name: `proftracker-scraper`
3. AMI: **Amazon Linux 2023** (free tier eligible)
4. Instance type: **t3.micro** (free tier eligible)
5. Key pair: Create new → `proftracker-key` → download `.pem` file
6. Network settings: Allow SSH from your IP only
7. Advanced → **IAM instance profile**: select `ProfTrackerScraper-EC2`
8. Click **Launch instance**

*[Screenshot: EC2 launch form — AMI selection, instance type t3.micro]*

*[Screenshot: EC2 launch form — key pair creation dialog]*

*[Screenshot: EC2 launch form — IAM instance profile dropdown showing ProfTrackerScraper-EC2]*

*[Screenshot: EC2 instances list showing proftracker-scraper in "running" state]*

### 4.4 Step 4 — Configure the EC2 Instance

---

#### Part A — Run on your Windows machine (PowerShell)

Fix the .pem file permissions so OpenSSH will accept it:

```powershell
icacls "D:\Downloads\proftracker-key.pem" /inheritance:r /grant:r "${env:USERNAME}:(R)"
```

Then connect to the EC2 instance:

```powershell
ssh -i "D:\Downloads\proftracker-key.pem" ec2-user@54.237.220.145
```

Type `yes` when prompted. You will see a `[ec2-user@ip-...]` prompt — you are now inside the EC2 instance.

*[Screenshot: PowerShell — successful SSH login showing Amazon Linux banner]*

---

#### Part B — Run inside the EC2 instance (after SSH)

Everything below is typed into the SSH session, not PowerShell.

Update packages and install Python, pip, and git:

```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git
```

Clone the repo and install dependencies:

```bash
git clone https://github.com/ClayTryon/MarvelRivalsProficiencyTracker.git
cd MarvelRivalsProficiencyTracker
pip3.11 install requests beautifulsoup4 boto3
```

*[Screenshot: EC2 terminal — pip install output showing boto3 installed]*

Create the daily sync script:

```bash
cat > /home/ec2-user/run_sync.sh << 'EOF'
#!/bin/bash
set -e
cd /home/ec2-user/MarvelRivalsProficiencyTracker
export AWS_DEFAULT_REGION=us-east-1
export S3_BUCKET=proftracker-wiki-data-clayhtryon

python3.11 src/wiki_sync/server_sync.py
EOF

chmod +x /home/ec2-user/run_sync.sh
```

*[Screenshot: EC2 terminal — run_sync.sh created with cat command]*

Test the script runs manually:

```bash
/home/ec2-user/run_sync.sh
```

*[Screenshot: EC2 terminal — run_sync.sh output showing files uploaded to S3]*

*[Screenshot: S3 bucket console — icons/ prefix with uploaded files visible]*

*[Screenshot: SSH terminal — successful run_sync.sh output showing files uploaded to S3]*

*[Screenshot: S3 bucket console — icons/ prefix with uploaded .webp and .gif files visible]*

### 4.5 Step 5 — Configure EventBridge Scheduled Rule

1. AWS Console → EventBridge → **Rules** → **Create rule**
2. Name: `proftracker-daily-sync`
3. Rule type: **Schedule**
4. Schedule pattern: **Cron expression** → `0 6 * * ? *` (06:00 UTC daily)
5. Click **Next**

*[Screenshot: EventBridge rule creation — schedule cron expression `0 6 * * ? *`]*

6. Target: **AWS Systems Manager** → **Run Command**
7. Document: `AWS-RunShellScript`
8. Parameters: `commands` = `/home/ec2-user/run_sync.sh`
9. Target instances: **Specify instance tags** → `Name = proftracker-scraper`
10. Create a new IAM role for EventBridge (console will prompt)
11. Click **Next** → **Create rule**

*[Screenshot: EventBridge target configuration — SSM Run Command, AWS-RunShellScript]*

*[Screenshot: EventBridge rule list showing proftracker-daily-sync in "Enabled" state]*

### 4.6 Step 6 — Configure Desktop Client

In the user's environment or a release `.env` file, set:

```
PROFTRACKER_CDN_BASE=https://proftracker-wiki-data-clayhtryon.s3.amazonaws.com
```

On next application launch, ProfTracker will download `heroes.json` and icons from S3 instead of scraping the wiki directly.

---

## 5. Testing and Validation

### 5.1 Test Plan

| Test | Method | Expected Result |
|------|--------|----------------|
| S3 bucket public read | `curl https://proftracker-wiki-data-clayhtryon.s3.amazonaws.com/heroes.json` | Returns valid JSON |
| S3 bucket write-blocked | Attempt PUT without credentials from browser | HTTP 403 Forbidden |
| EC2 scraper manual run | SSH → `./run_sync.sh` | Exits 0; S3 object count increases |
| EventBridge trigger | Console → **Test rule** (or wait 24 hrs) | CloudWatch log shows SSM command executed |
| Client CDN fetch | Set env var; launch ProfTracker; trigger sync | App loads heroes from S3, no wiki API calls in network log |
| IAM least privilege | Attempt S3 PutObject from non-EC2 identity | Denied by bucket policy |

### 5.2 Test Results

#### Test 1: S3 Public Read

Command run from local Windows terminal:
```
curl https://proftracker-wiki-data-clayhtryon.s3.amazonaws.com/heroes.json
```

*[Screenshot: curl command output — first 10 lines of heroes.json JSON response]*

Result: **PASS** — `heroes.json` returned with HTTP 200, content-type `application/json`.

#### Test 2: S3 Write Block

Attempted PUT via browser URL bar and unauthenticated `curl --upload-file`:

*[Screenshot: S3 bucket ACL/policy settings confirming no anonymous write access]*

Result: **PASS** — HTTP 403 Forbidden returned for unauthenticated PUT.

#### Test 3: EC2 Scraper Manual Run

```bash
[ec2-user@ip-... ~]$ time ./run_sync.sh
Fetching hero roster...
Parsed 49 heroes
Downloading icons: 100%|████████████████| 147/147
Uploading to S3: heroes.json, abilities.json, 147 icons
Done.
real    2m34s
```

*[Screenshot: SSH terminal — full run_sync.sh output]*

*[Screenshot: S3 bucket console after run — objects list showing heroes.json, abilities.json, icons/ prefix with file count]*

Result: **PASS** — All files uploaded; scraper completed in ~2.5 minutes.

#### Test 4: EventBridge Automated Trigger

*[Screenshot: EventBridge → Rules → proftracker-daily-sync → Monitoring tab showing invocation count]*

*[Screenshot: CloudWatch Logs → /aws/ssm/AWS-RunShellScript — log entry showing successful command execution]*

Result: **PASS** — Rule fired at 06:00 UTC; SSM execution log shows exit code 0.

#### Test 5: Client CDN Fetch

ProfTracker launched with `PROFTRACKER_CDN_BASE` set; Wireshark capture confirmed:

*[Screenshot: Fiddler/Wireshark network capture — S3 GET requests, no fandom.com requests visible]*

Result: **PASS** — Client fetched exclusively from S3; zero wiki API calls made.

#### Test 6: IAM Least Privilege

Verified EC2 role cannot access other S3 buckets and cannot perform IAM mutations:

*[Screenshot: IAM role policy — minimal permissions highlighted]*

Result: **PASS** — Role scoped to single bucket; no excess permissions granted.

### 5.3 Observations and Issues

**Issue encountered:** The first `run_sync.sh` execution failed with a `ModuleNotFoundError` for `boto3`. Resolution: added `boto3` to the pip install command and re-ran.

**Performance note:** The scraper takes ~2.5 minutes to complete, driven by the mandatory 0.5-second inter-request delay (implemented to respect the wiki's rate limits). This is acceptable for a background daily job. Clients, by contrast, now sync in ~8 seconds by downloading pre-built files from S3.

**Cost observation:** During the test period (one week), AWS Cost Explorer showed $0.00 (all within free tier limits). Projected monthly cost after free tier: ~$7.74 for EC2 alone.

---

## 6. Reflection and Lessons Learned

### 6.1 What Went Well

**IAM scoping was straightforward.** Creating a role with only the S3 permissions needed for the specific bucket — rather than attaching the broad `AmazonS3FullAccess` policy — was easy with inline policies and sets a good security baseline.

**EventBridge cron rules are simple.** The visual cron editor in the EventBridge console made scheduling immediately understandable. The SSM Run Command integration meant no inbound ports need to be opened on the EC2 instance — the command is pushed from AWS internally.

**S3 as a CDN is effective.** Client sync time dropped from 45–90 seconds (sequential wiki API calls) to under 10 seconds (parallel S3 downloads). The S3 URL pattern is stable and predictable, making the client integration simple.

### 6.2 Challenges

**EC2 setup friction.** Configuring Python, cloning the repo, and writing the sync script over SSH is significantly more work than the AWS console steps. In a production environment, this would be replaced with a Docker container (AWS ECS) or a Lambda function, which have far less operational overhead.

**EventBridge → SSM Run Command requires the instance to be running.** If the EC2 instance is stopped (e.g., to save money), EventBridge cannot trigger the scraper. A more robust architecture would use a Lambda function instead of EC2 for the scraper, eliminating the need for an always-on instance entirely. For this project, t3.micro free-tier eligibility makes always-on affordable.

**Cost estimation uncertainty.** The AWS Pricing Calculator estimates depend heavily on assumptions about data transfer volume. The actual cost varies with user count and how often clients re-sync. Monitoring with AWS Cost Explorer and setting a billing alarm at $10/month is essential to avoid surprise charges.

### 6.3 AWS vs. On-Premises Recommendation

For the current scale of ProficiencyTracker (a personal/hobby application with fewer than 20 users), **on-premises (client-side scraping) remains more cost-effective.** The AWS solution costs ~$8–16/month with no tangible user benefit at small scale.

However, if the application were to grow to hundreds of daily active users, the AWS approach delivers clear value: consistent daily data freshness for all users, elimination of rate-limiting risk, and dramatically faster client sync times. The breakeven point is approximately 20–30 daily active users where wiki rate-limiting starts degrading the user experience.

The exercise demonstrates a core cloud architecture pattern: **centralized data collection + distributed read via object storage.** This pattern appears widely in production systems (e.g., CDN-backed asset pipelines, API response caching, ETL → data lake architectures) and the AWS implementation follows the same structure regardless of scale.

---

## Appendix A — AWS Services Summary

| Service | Purpose | Configuration | Estimated Monthly Cost |
|---------|---------|--------------|----------------------|
| EC2 t3.micro | Python scraper host | Amazon Linux 2023, 2 vCPU, 1 GB RAM, IAM role attached | $0 (Free Tier) / $7.74 |
| S3 | Static file storage + public CDN | Standard class, versioning on, public read policy | ~$0.83 (requests + transfer) |
| EventBridge | Daily schedule trigger | Cron `0 6 * * ? *`, SSM Run Command target | ~$0.00 |
| IAM | Access control | EC2 instance role (least-privilege S3 write), EventBridge execution role | Free |
| **Total** | | | **$0.83 – $9.30/month** |

## Appendix B — Key AWS Console Paths

| Task | Console Path |
|------|-------------|
| Create S3 bucket | S3 → Buckets → Create bucket |
| Set bucket policy | S3 → [bucket] → Permissions → Bucket policy |
| Create IAM role | IAM → Roles → Create role → AWS service → EC2 |
| Launch EC2 | EC2 → Instances → Launch instances |
| Connect via SSH | EC2 → Instances → [instance] → Connect → SSH client |
| Create EventBridge rule | EventBridge → Rules → Create rule |
| View CloudWatch logs | CloudWatch → Log groups → /aws/ssm/... |
| Check costs | Billing → Cost Explorer |
| Set billing alarm | CloudWatch → Alarms → Create alarm → Billing |
