# 🦁 AI Picture Picker (AIPP)

**Wildlife Photo Intelligence Engine** — AI-powered photo culling and storytelling for wildlife photographers.

---

## What It Does

AIPP processes thousands of RAW wildlife photos and uses Claude Vision AI to:
- Score every photo on technical quality and storytelling merit
- Automatically sort into tiers: Great / Good / Review / Delete
- Generate editing recommendations (Lightroom + Topaz DeNoise)
- Create social media narratives from your best shots

Built specifically for wildlife photographers shooting **3,000–5,000 photos per safari trip**.

---

## Features

### 📊 Dashboard
- Trip overview with keep rate, session average, top shots
- AI session summary with actionable insights
- Category breakdown and performance vs benchmarks

### 🖼 Gallery
- Fast browsing of all photos with scores and tiers
- Filter by category, tier, or score range
- AI scoring with progress tracking

### 📈 Analytics
- Score distribution and tier breakdowns
- Dimension analysis (Eyes/Focus, Moment, Exposure, etc.)
- Category performance vs industry benchmarks
- Export to Lightroom/Capture One CSV

### ⭐ Rate Photos
- Human review queue for borderline photos
- Side-by-side: photo + AI reasoning + EXIF + edit suggestions
- Keyboard shortcuts (G/O/D) for fast rating

### 📝 Story Studio *(NEW)*
- Select keepers and generate platform-specific narratives
- Instagram captions + carousel order + hashtags
- WhatsApp status, Twitter, Facebook posts
- Field notes integration for authentic storytelling

---

## Tech Stack

- **Framework:** Streamlit
- **AI:** Claude Sonnet 4.6 (Anthropic API)
- **Database:** SQLite
- **Image Processing:** Pillow, rawpy
- **Charts:** Plotly

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Anthropic API key

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/AIPP.git
cd AIPP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .streamlit/secrets.toml
mkdir .streamlit
echo 'ANTHROPIC_API_KEY = "your-api-key-here"' > .streamlit/secrets.toml

# Run the app
streamlit run app.py
```

### Project Structure

```
AIPP/
├── app.py                  # Main Streamlit app (all 6 pages)
├── src/
│   ├── database.py         # SQLAlchemy models (Trip, Photo)
│   ├── services/
│   │   ├── ingestor.py     # File discovery and EXIF extraction
│   │   └── scorer.py       # Claude Vision API scoring
│   └── ui/
│       └── styles.py       # CSS and UI components
├── requirements.txt
├── .gitignore
├── README.md
└── .streamlit/
    └── secrets.toml        # API keys (not committed)
```

---

## Deployment (Streamlit Cloud)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add `ANTHROPIC_API_KEY` in Secrets
5. Deploy!

---

## Usage Workflow

1. **New Trip** — Upload RAW photos from a safari/birding trip
2. **Gallery** — Run AI scoring (processes in background)
3. **Dashboard** — Review top shots and session insights
4. **Analytics** — Deep dive into category performance
5. **Rate Photos** — Human review of borderline shots
6. **Story Studio** — Generate social media posts from keepers
7. **Export** — Download CSV for Lightroom/Capture One

---

## Cost & Performance

- **API Cost:** ~$0.003–0.006 per photo (Claude Vision)
- **Speed:** 45–90 min for 1,000 photos (async processing)
- **Storage:** SQLite database + thumbnails only (RAW files stay local)

**Cost Optimization:** Use Anthropic Batch API for 50% discount on non-real-time scoring.

---

## Roadmap

- [ ] Batch API integration for 50% cost reduction
- [ ] Similarity/burst detection
- [ ] Personal taste model (learns from your ratings)
- [ ] Direct social media posting (Instagram API)
- [ ] Lightroom plugin (native integration)

---

## License

MIT License — See LICENSE file for details

---

## Contributing

Pull requests welcome! For major changes, please open an issue first.

---

## Author

Built by a wildlife photographer who got tired of spending 4 hours culling after every safari.

**Questions?** Open an issue or reach out via [your contact method]

---

🦁 **Happy Culling!**
