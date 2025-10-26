# 🐉 HydraScan - The AI-Powered Security Automation App

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blueviolet.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-informational.svg)

**HydraScan** is no longer just a script; it's a full-featured desktop application that brings the power of an entire Kali Linux suite and a GenAI analyst to your fingertips. It automates penetration testing by running multiple security modules in parallel and uses Google Gemini to instantly analyze raw data, transforming it into executive-ready reports.

---

## [<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/907c7047-2bed-45d4-badf-f2736ba91ea3" />]


---

## 🎯 The Problem vs. The Solution

* **The Problem:** Security audits are slow, resource-intensive, and require expert-level analysis. Generating a clear, actionable report from raw tool output (like Nmap or SQLMap) can take days.
* **The HydraScan Solution:**
    1.  **Automate & Parallelize:** Run comprehensive scans (Recon, Web, API, Cloud, etc.) simultaneously, not sequentially.
    2.  **Analyze with AI:** Automatically feed all technical findings into Google Gemini.
    3.  **Instant Reports:** Generate professional HTML reports with executive summaries, risk levels, CVSS scores, and remediation steps in *seconds*.

HydraScan bridges the gap between technical vulnerability data and actionable business intelligence.

## 🚀 Core Features

* **🖥️ Desktop Application:** A clean, simple, and powerful GUI built with CustomTkinter. No command-line-fu required.
* **⚡ AI-Powered Reporting:** Leverages Google Gemini to act as an AI security analyst, turning complex data into clear, professional reports.
* **🐳 One-Click Secure Environment:** All tools run in an isolated Kali Linux Docker container managed by the app. Zero setup or "dependency hell."
* **⏱️ Blazing-Fast Parallel Scans:** The multi-threaded engine (`concurrent.futures`) runs modules simultaneously, drastically cutting down assessment time.
* **🧩 Comprehensive & Modular:** Covers the entire attack surface with distinct modules:
    * **Reconnaissance:** `whois`, `dig`, `subfinder`, `nmap`, `nikto`
    * **Web Application:** `gobuster`, `sqlmap`, `dalfox` (XSS), `commix`
    * **API Security:** `kiterunner` / `ffuf`
    * **Internal Network:** `nmap` (Discovery), `Responder`
    * **Cloud (AWS):** `Prowler` (CIS Audits)
    * **Mobile (Android):** `apkleaks`

---

## 🏃‍♂️ Getting Started (As an App)

This is a ready-to-use prototype. No Python or cloning required for basic use.

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Must be installed and running)
* A [Google Gemini API Key](https://ai.google.dev/pricing)

### Installation
1.  Go to the [**Releases**] https://github.com/mgorkemklc/HydraScan page of this repository.
2.  Download the latest `HydraScan.exe` file.
3.  Run the application!

*(On the first run, HydraScan will build its internal Kali Docker image. This may take a few minutes, but only happens once.)*

---

## 🏗️ Vision & Investment Roadmap (The Future)

HydraScan is now a functional prototype (`app.exe`) ready for the next level. The vision is to scale this into a full-fledged, collaborative **SaaS platform**.

The foundation for this is already being laid in the `hydrascan_web/` directory (a Django project).

**We are actively seeking investment to achieve our roadmap:**
* **Phase 1 (SaaS MVP):** Transition the desktop app's logic to a central, multi-tenant Django web application.
* **Phase 2 (Collaboration):** Introduce team dashboards, role-based access control (RBAC), and project management.
* **Phase 3 (CI/CD Integration):** Provide API hooks for DevSecOps, allowing HydraScan to run automatically in developer pipelines.
* **Phase 4 (Expansion):** Add support for Azure, GCP, and advanced IoT/OT testing modules.

---

## 👨‍💻 For Developers (Running from Source)

Want to contribute? You can run the app from its Python source.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/](https://github.com/)[KULLANICI_ADINIZ]/HydraScan.git
    cd HydraScan
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python app.py
    ```

## 🤝 Contributing

Contributions are what make the open-source community amazing. Any contributions you make are **greatly appreciated**. Please open an issue first to discuss what you would like to change.

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## ⚠️ Disclaimer

This tool is for educational purposes and authorized, legal penetration testing activities **only**. The developer assumes no liability and is not responsible for any misuse or damage caused by this program.
