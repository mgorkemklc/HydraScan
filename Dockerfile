FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

# 1. TEMEL ARAÇLAR (Amass'ı buradan çıkardık, elle kuracağız)
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    nmap nikto sqlmap whois dnsutils \
    gobuster hydra \
    curl wget git unzip make gcc \
    pciutils net-tools iputils-ping \
    libpcap-dev \
    default-jdk jadx \
    apktool \
    dirb \
    wordlists \
    gzip \
    golang \
    sslscan \
    && rm -rf /var/lib/apt/lists/*

# 2. GO ORTAMI
ENV GOPATH=/root/go
ENV PATH=$PATH:$GOPATH/bin:/usr/local/go/bin

# 3. WORDLIST HAZIRLIĞI
RUN if [ -f /usr/share/wordlists/rockyou.txt.gz ]; \
    then \
        gunzip /usr/share/wordlists/rockyou.txt.gz; \
    fi

# 4. MODERN ARAÇLAR (BINARY KURULUM - HATASIZ)

# Dalfox
RUN go install github.com/hahwul/dalfox/v2@latest

# Nuclei (Direkt İndirme)
RUN wget https://github.com/projectdiscovery/nuclei/releases/download/v3.3.6/nuclei_3.3.6_linux_amd64.zip \
    && unzip nuclei_3.3.6_linux_amd64.zip \
    && mv nuclei /usr/local/bin/ \
    && rm nuclei_3.3.6_linux_amd64.zip

# Subfinder (Direkt İndirme)
RUN wget https://github.com/projectdiscovery/subfinder/releases/download/v2.6.6/subfinder_2.6.6_linux_amd64.zip \
    && unzip subfinder_2.6.6_linux_amd64.zip \
    && mv subfinder /usr/local/bin/ \
    && rm subfinder_2.6.6_linux_amd64.zip

# Amass (Direkt İndirme - Fix)
# Kali reposundaki bozuk sürüm yerine orijinal binary kullanıyoruz
RUN wget https://github.com/owasp-amass/amass/releases/download/v3.23.3/amass_linux_amd64.zip \
    && unzip amass_linux_amd64.zip \
    && mv amass_linux_amd64/amass /usr/local/bin/ \
    && rm -rf amass_linux_amd64*

# 5. PYTHON ARAÇLARI
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PATH="/root/go/bin:${PATH}"
RUN pip install --upgrade pip setuptools wheel
RUN pip install wapiti3 commix apkleaks

WORKDIR /app
CMD ["/bin/bash"]