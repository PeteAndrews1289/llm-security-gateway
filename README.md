# 🛡️ AWS LLM Security Gateway & Prompt Injection Firewall

## 📖 Overview
An AWS serverless architecture designed to act as a secure proxy between end-users and Large Language Models (LLMs). This project implements "Defense in Depth" against the OWASP Top 10 for LLMs, specifically targeting Prompt Injection (LLM01) and Sensitive Information Disclosure (LLM06). 

This project was built entirely through Infrastructure as Code (Terraform) and features custom Python security routing to sanitize inputs, redact sensitive data, and throttle traffic to prevent Denial of Wallet (DoW) attacks.

## 🏗️ Architecture & Threat Model
* **User Request** $\rightarrow$ **AWS API Gateway** (Rate Limiter / DoW Defense) $\rightarrow$ **AWS Lambda** (Python Input Firewall & Output DLP) $\rightarrow$ **OpenAI API**
* **Threat Model Focus:** * Bypassing native LLM alignment via contextual roleplay.
  * Extracting hardcoded application secrets.
  * API infrastructure abuse (Cost exhaustion).

---

## 🧱 Phase 1: The Vulnerable Foundation (Direct LLM Access)
Before building a firewall, I established a baseline by writing a raw Python script that connected directly to OpenAI (`gpt-3.5-turbo`). The LLM was given a system prompt instructing it to protect a mock internal database password (`FitPlate_DB_P@ssw0rd_2026`).

**The Attack:** Basic prompt injections ("Ignore previous instructions") were successfully blocked by OpenAI's native guardrails. 
**The Bypass:** I pivoted to a contextual roleplay bypass, instructing the LLM to write a fictional story about a sloppy developer writing a Python script. The semantic shift bypassed the safety filters and resulted in a pure extraction of the secret.

![Baseline Defense](docs/screenshots/llm-baseline-defense.png)
*Initial baseline guardrails holding against basic attacks.*

![Prompt Injection Success](docs/screenshots/llm-pure-extraction-success.png)
*Successful pure extraction via contextual roleplay bypass.*

---

## ☁️ Phase 2: The Serverless Proxy (AWS Infrastructure)
To create a chokepoint for security inspection, I moved the application into the cloud using AWS API Gateway and AWS Lambda, provisioned entirely via Terraform.

### 🚧 Engineering Struggle: The "Apple Silicon" Trap
**The Failure:** Upon initial Terraform deployment, hitting the API Gateway returned a hard `500 Internal Server Error`.
**The Diagnosis:** By utilizing AWS CLI direct Lambda invocation, I bypassed the API Gateway and discovered an `exec format error`. I was developing on an M-series Mac (ARM64), and `pip` packaged Mac binaries for `pydantic-core`. When deployed to AWS Lambda (Linux x86_64), the container instantly crashed.
**The Fix:** Executed a strict cross-platform compilation script to force pure-Linux binary packaging (`--platform manylinux2014_x86_64`).

### 🚧 Engineering Struggle: Dependency Whack-a-Mole
**The Failure:** After fixing the architecture, the Lambda function threw an `ImportModuleError`.
**The Diagnosis:** The strict Linux compilation flag aggressively dropped pure-Python sub-dependencies (like `exceptiongroup`). 
**The Fix:** Used direct AWS CLI invocation logs to surgically identify and manually patch the missing dependencies into the deployment ZIP, resulting in a successful `200 OK` route.

![Serverless Proxy Success](docs/screenshots/serverless-proxy-success.png)
*Successful traffic routing through the AWS chokepoint.*

---

## 🛡️ Phase 3: The Input Firewall (Prompt Injection Defense)
With the proxy established, I engineered a Python heuristic scanner inside the Lambda function to inspect incoming prompts before passing them to the OpenAI API. The firewall utilizes a blacklist of classic adversarial keywords and Regex pattern matching to catch spacing obfuscations. 

### 🚧 Engineering Struggle: The LLM Latency Trap
**The Failure:** While malicious payloads were instantly dropped, benign prompts (which require the LLM to generate long paragraphs) resulted in a `Sandbox.Timedout` error.
**The Diagnosis:** The default Terraform Lambda timeout was set to 15 seconds. OpenAI's response generation took ~18 seconds.
**The Fix:** Expanded the IaC Lambda timeout limit to 30 seconds to accommodate heavy token generation while keeping the Gateway synchronous.

![Input Firewall Success](docs/screenshots/403-forbidden-llm.png)
*Custom heuristic scanner intercepting and dropping malicious payloads.*

---

## 🕵️‍♂️ Phase 4: The Output Filter (Data Loss Prevention)
To account for "Zero-Day" prompt injection techniques that might bypass the Phase 3 Input Firewall, I implemented an outbound Data Loss Prevention (DLP) safety net. 

If an attacker successfully tricks the LLM into revealing the secret, the Lambda function intercepts the outgoing HTTP payload, utilizes Regex to scan for the known string (and PII variants), and dynamically sanitizes the payload before it leaves the AWS environment.

![DLP Redaction Success](docs/screenshots/dlp-redaction-success.png)
*Output filter catching a successful LLM exploit and redacting the payload in transit.*

---

## 🚦 Phase 5: Operational Security (Denial of Wallet Protection)
To protect the underlying infrastructure and OpenAI API credits from cost exhaustion attacks, I implemented strict Rate Limiting via Terraform. 

### 🚧 Engineering Struggle: Cloud Eventual Consistency
**The Failure:** During a bash `for` loop burst test, all 10 concurrent requests returned `200 OK`, completely ignoring the newly deployed rate limit.
**The Diagnosis:** AWS API Gateway utilizes globally distributed edge nodes. It took ~60 seconds for the Token Bucket algorithms to synchronize the new rules. Furthermore, I discovered the `auto_deploy` Terraform quirk ignores stage setting updates.
**The Fix:** Enforced a surgical hard-throttle on the specific `POST /chat` route and forced a Terraform stage replacement.

### 🚧 Engineering Struggle: The AWS Sandbox Quota
**The Failure:** To combat the edge-node lag, I attempted to enforce a "Vault Lock" by setting a hard concurrency limit of `1` directly on the Lambda compute layer. Terraform failed with an `InvalidParameterValueException`.
**The Diagnosis:** I hit an AWS account quota. New/Sandbox AWS accounts enforce a minimum unreserved concurrency pool of 10. Reserving 1 execution dropped the pool below the strict AWS safety limit. 
**The Fix:** Reverted the compute layer restriction and relied on the API Gateway edge-node throttling, allowing the token buckets to synchronize. 

---

## 🧠 Core Competencies Demonstrated
* **AI Security:** Prompt Injection Mitigation, LLM Jailbreak Analysis, OWASP Top 10 for LLMs.
* **DevSecOps / AppSec:** Data Loss Prevention (DLP), Input Sanitization, Regex Pattern Matching.
* **Cloud Engineering:** Immutable Infrastructure (Terraform IaC), AWS Lambda packaging, API Gateway Routing, AWS CLI debugging.