# 🚨 IncidentPilot — Memory-Augmented Production Incident Response Agent

IncidentPilot is an AI-powered DevOps agent built for real-world production incident triage, powered by **Vectorize Hindsight** for persistent memory and **Groq** for high-speed LLM inference.

## 🎯 Problem Statement
During production outages, every minute counts. Traditional AI assistants operate statelessly—giving standard, generic advice without context of past post-mortems, recurring infrastructure bugs, or specific system runbooks.

## 🧠 How Hindsight Memory Powers IncidentPilot
IncidentPilot utilizes **Hindsight Persistent Memory** to bridge this gap:
1. **Retain Stage**: After every resolved incident, post-mortems (root causes, symptoms, and exact fix commands) are ingested into Hindsight memory banks.
2. **Recall Stage**: When new production alerts or log spikes occur, IncidentPilot queries Hindsight to fetch matching historical incidents before producing diagnostic steps.
3. **Continuous Learning**: The agent gets smarter over time, drastically reducing Mean Time To Resolution (MTTR).

## 🚀 Quickstart Guide

### 1. Installation
```bash
git clone [https://github.com/your-username/incident-pilot.git](https://github.com/your-username/incident-pilot.git)
cd incident-pilot
pip install -r requirements.txt