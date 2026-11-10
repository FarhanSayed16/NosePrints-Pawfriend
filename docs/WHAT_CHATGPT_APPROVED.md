# What ChatGPT approved — plain English

**Date:** 10 November 2026

ChatGPT did **not** ask you to retrain models or change the live app.

It gave **permission for Cursor to run offline science experiments** and write reports.

---

## In one sentence

> Measure how we match dogs and how often unknown dogs get false IDs — **without changing production**.

---

## What YOU need to do

| You | Not you |
|-----|---------|
| Read the result docs when Cursor finishes | Retrain / promote ONNX |
| Later: collect real phone dog photos (Index 1) | Change `.env` thresholds |
| Approve any future model change | Buy Nexdata |

---

## What Cursor is doing now (approved)

| Index | Name | Meaning |
|------:|------|---------|
| **2** | Experiment A | Compare 4 ways to use multiple nose prints (max vs mean vs quality-weighted). **Recommend only — no code change to matcher yet.** |
| **4** | Experiment C | Measure false accepts on **unregistered** dogs at 0.56 and 0.60 using **production** embedding. |
| **3** | Dataset audit | List what data we already have / what is safe to download. **No paid downloads.** |

Then Cursor writes:

- `docs/EXPERIMENT_A_MULTIPRINT_RESULTS.md`
- `docs/EXPERIMENT_C_OPEN_SET_RESULTS.md`
- refresh `docs/DATASET_INVENTORY.md`
- `docs/NEXT_ML_DECISION_REPORT.md` (final summary + what Farhan must provide next)

---

## Hard rules ChatGPT locked (Cursor must obey)

- Do **not** replace production ONNX  
- Do **not** train new models  
- Do **not** change thresholds / `.env`  
- Do **not** wipe the database  
- Do **not** buy Nexdata  
- Staff confirmation stays mandatory  

---

## After these experiments

You will get evidence-based answers like:

- Keep current **max-over-prints** matching, or try mean templates later  
- Is strict **0.60** sensible on lab open-set?  
- What data Farhan must collect before any fine-tune  

**Then** (separate approval) you may decide to implement a matcher change or start phone pilot collection.
