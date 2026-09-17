# CTF Writeups & Problem Solutions

A collection of writeups, analysis, and solution scripts for recent CTF and forensics challenges.

---

## 🚩 Solved Challenges

### 1. [Challenge Name / Title](#) <!-- Replace # with the link to the problem or file -->
- **Category:** Forensics / SVG Analysis / Steganography
- **Problem Link / File:** [`challenge_1.svg`](./challenge-1/challenge_1.svg) <!-- Or external link e.g. https://ctf.example.com/challenges/1 -->
- **Difficulty:** Easy–Medium

#### 📋 Challenge Description
The flag was hidden inside an SVG vector graphics file. When rendered in standard viewers or browsers, the text containing the flag was completely invisible or collapsed due to sub-pixel styling configurations.

#### 🔍 Analysis & Solution
1. **Source Inspection:** Inspected the raw SVG XML structure using terminal text tools.
2. **Identifying the Anomaly:** Located `<text>` and `<tspan>` nodes configured with an extremely tiny font size (`font-size:0.00352781px`).
3. **Reconstructing the Flag:** Extracted and concatenated the character segments across the consecutive `<tspan>` nodes:
   - `<tspan id="tspan3764">F { 3 n h 4 n </tspan>`
   - `<tspan id="tspan3752">c 3 d _ a a b 7 2 9 d d }</tspan>`

#### 🏁 Flag
```text
F{3nh4nc3d_aab729dd}
