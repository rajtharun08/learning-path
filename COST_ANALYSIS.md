# Cost Analysis: LearningPath POC Scalability (Optimized)

This document provides a financial projection for operating the LearningPath platform at a production scale of **50,000 monthly users**. The architecture utilizes a **Hybrid Recommendation System** to balance high performance with minimal operational overhead.

## 1. Base Infrastructure (Fixed Monthly Costs)
These are the foundational services required to host the FastAPI backend, manage the PostgreSQL database, and serve the frontend via a global CDN.

| Component | Service Provider | Monthly Estimate | Purpose |
| :--- | :--- | :--- | :--- |
| **App Server** | Render / AWS EC2 | **₹2,100** | Hosts FastAPI backend and scoring engine. |
| **Managed DB** | Supabase / PostgreSQL | **₹1,250** | Stores user profiles, skills, and history. |
| **Frontend / CDN** | Vercel / Netlify | **₹1,650** | Hosts the UI and serves static assets. |
| **Security / SSL** | Cloudflare / AWS WAF | **₹800** | SSL encryption and traffic protection. |
| **Total Base Cost** | | **₹5,800** | |

---

## 2. Logic Implementation: Scenario Comparison
This section compares three implementation strategies. We assume a **50% Cache Efficiency** for both Optimized scenarios.

### Request Distribution
* **Total Users:** 50,000 
* **Beginner Tier:** 30,000 (Processed locally via Rules-Engine @ **₹0**)
* **Advanced Tier:** 20,000 (Processed via AI Engine)

| Metric | Scenario A: Standard (Mid-Tier) | Scenario B: Optimized (Mid-Tier) | Scenario C: Optimized (Low-Tier) |
| :--- | :--- | :--- | :--- |
| **Model Type** | GPT-4o / Gemini Pro | GPT-4o / Gemini Pro | **GPT-4o mini / Gemini Flash** |
| **Cost per Request** | ₹1.20 | ₹1.20 | **₹0.15** |
| **Caching (Redis)** | No | Yes (₹1,200) | **Yes (₹1,200)** |
| **AI API Subtotal** | ₹24,000 | ₹12,000 | **₹1,500** |
| **Variable Total** | ₹24,000 | ₹13,200 | **₹2,700** |

---

## Summary Comparison (Monthly Total)

| Cost Category | No Caching (Mid-Tier) | Optimized (Mid-Tier) | Optimized (Low-Tier) |
| :--- | :--- | :--- | :--- |
| **Base Infrastructure** | ₹5,800 | ₹5,800 | ₹5,800 |
| **Variable Logic** | ₹24,000 | ₹13,200 | ₹2,700 |
| **Total Monthly Cost** | **₹29,800** | **₹19,000** | **₹8,500** |

### **Estimated Savings (Scenario C vs A): ~71% reduction in total operational cost.**

## Conclusion

1. **Local Offloading:** Beginner paths are handled by the internal Python engine at zero cost.
2. **Model Tiering:** Using high-efficiency models (4o-mini/Flash) for curriculum generation reduces API fees by 87%.
3. **Result Caching:** A Redis layer prevents paying for the same recommendation twice for users with identical goals.

### Note
* **Implementation Status:** The current Backend POC focuses on **Scenario A** (Core functional logic and Scoring Algorithm). 
* **Future Roadmap:** The Redis Caching Layer and Low-Tier Model integration are currently **architectural proposals** intended for the next phase of development to ensure long-term financial sustainability.
* **Cost Variability:** All estimates are approximate. Actual costs may vary based on real-time traffic patterns, specific AI model token usage, and infrastructure scaling policies.
