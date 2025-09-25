# 🐉 HydraScan - An Intelligent & Parallel Security Testing Automation Framework

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blueviolet.svg)
![Docker](https://img.shields.io/badge/Docker-Required-informational.svg)

**HydraScan** is a Docker-based, modular, and intelligent penetration testing automation framework designed to provide a proactive defense against modern cybersecurity threats. It integrates the most popular and effective open-source security tools under a single umbrella, executes test modules in parallel to significantly reduce assessment time, and leverages the Google Gemini AI to transform raw technical findings into actionable, comprehensive reports.

---

## 🚀 Core Features

* **⚡ Parallel Test Execution:** Utilizes `concurrent.futures` to run reconnaissance, web, and API tests simultaneously, drastically reducing the overall testing duration.
* **🤖 AI-Powered Reporting:** Sends raw tool outputs to the Google Gemini API to generate professional HTML reports for each finding, complete with risk levels, CVSS scores, executive summaries, and technical remediation steps.
* **🐳 Dockerized & Isolated Environment:** All tools and dependencies run inside a dynamically created Docker image based on `kalilinux/kali-rolling`. This eliminates the need for any installation or configuration on your host machine.
* **🧩 Modular Architecture:** Each security domain is isolated in its own Python module, which facilitates the easy addition of new tools and test cases.
* **🌐 Comprehensive Scanning Capabilities:**
    * 🎯 **Reconnaissance:** `whois`, `dig`, `subfinder`, `nmap` (all ports), `nikto`
    * 💻 **Web Application:** `gobuster`, `sqlmap`, `dalfox` (modern XSS scanner), `commix`, `dirb`
    * 🔗 **API Security:** `ffuf` for discovering common API endpoints.
    * 🏢 **Internal Network & AD:** Host discovery with `nmap`, hash-capturing attempts with `Responder`.
    * ☁️ **Cloud (AWS):** CIS benchmark audits with `Prowler`, S3 bucket enumeration.
    * 📱 **Mobile (Android):** Static secret analysis with `apkleaks`, decompilation with `apktool`.
    * 📶 **Wireless:** WPA/WPA2 handshake capturing and cracking attempts with `airmon-ng`, `airodump-ng`, and `aircrack-ng`.
* **📊 Dynamic Report Visualization:** Integrates with `QuickChart.io` to generate pie charts in reports, visualizing the distribution of findings by risk level.

---

## 🛠️ Setup & Usage

### 🔑 Prerequisites:
* [Docker](https://www.docker.com/get-started)
* [Python 3.9+](https://www.python.org/downloads/)
* A Google Gemini API Key

### 👣 Steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mgorkemklc/HydraScan.git
    cd hydrascan
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: It is recommended to create a `requirements.txt` file containing `google-generativeai` and `tqdm`.)*

3.  **Run the application:**
    ```bash
    python main.py
    ```

4.  **Enter the required information when prompted:**
    * Target domain (e.g., `example.com`, `localhost:3000`)
    * Internal network IP range (optional)
    * AWS keys (optional)
    * Path to APK file (optional)
    * Your Google Gemini API key

On its first run, the application will automatically build a Docker image named `pentest-araci-kali:v1.5` containing all the necessary tools. This process may take some time. Subsequent runs will skip this step.

---

## 🏗️ Architecture

The project consists of several modules, each focused on a specific security domain:

* `main.py`: Manages the main application flow, user inputs, and module orchestration.
* `docker_helper.py`: Builds the Kali Linux-based Docker image and ensures commands are executed securely within the container.
* `report_module.py`: Collects all test outputs, analyzes them with Gemini AI, and transforms the results into a professional HTML report.
* **Testing Modules:**
    * `recon_module.py`: Passive and active reconnaissance.
    * `web_app_module.py`: Web application vulnerability scanning.
    * `api_module.py`: API endpoint discovery.
    * `internal_network_module.py`: Internal network discovery and Active Directory tests.
    * `cloud_module.py`: AWS security configuration audits.
    * `mobile_module.py`: Android application static analysis.
    * `wireless_module.py`: Wireless network security testing.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. Please discuss the changes you wish to make by creating an issue before making a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingTool`)
3.  Commit your Changes (`git commit -m 'Add some AmazingTool'`)
4.  Push to the Branch (`git push origin feature/AmazingTool`)
5.  Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## ⚠️ Disclaimer

This tool is intended for educational purposes and for use in authorized, legal penetration testing activities only. Unauthorized use is strictly prohibited. The developer assumes no liability and is not responsible for any misuse or damage caused by this program. Always act responsibly and ethically.
