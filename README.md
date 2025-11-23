## **📦 Download YouTube Videos in Terminal (Textual UI + PyTubeFix)**

A fully interactive terminal-based YouTube downloader built using **Textual**, **Rich**, and **PyTubeFix**.
Designed with a clean TUI, real-time progress updates, and both **video & audio selection** before downloading.

---

### **✨ Key Features**

| Feature                   | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| 🎛 **Interactive TUI**    | Navigate video/audio streams using keyboard & mouse  |
| 🔍 **Metadata Fetching**  | Displays all available resolutions, formats, codecs  |
| 📥 **Clean Filenames**    | Auto-formatted filenames with proper extensions      |
| ⏱ **Real-time progress**  | Shows speed, ETA, percent, and progress bar          |
| 🎉 **Completion screen**  | Confirms file details after download                 |
| 🧵 **Threaded execution** | UI remains responsive during download                |
| 🚫 **No async required**  | Uses **standard YouTube object**, not `AsyncYouTube` |

---

### **🛠 Dependencies**

Make sure these are installed:

```bash
pip install textual rich pytubefix
```

---

### **▶ Run**

```bash
python YoutubeFixed_Normal.py
```

---

### **📌 How It Works**

1. Enter a **YouTube video URL** in the main screen.
2. Script fetches **all available streams** (audio + video).
3. Select a stream → automatically opens download UI.
4. Download begins with live progress metrics.
5. A **congratulations screen** opens after completion.

---

### **📜 Tech Stack**

| Component           | Library                                     |
| ------------------- | ------------------------------------------- |
| UI Rendering        | `textual`, `rich`                           |
| YouTube Downloading | `pytubefix`                                 |
| Threading           | Python Standard Library                     |
| Styling             | Gradients, Tables, Containers (Textual CSS) |

---

### **📂 Project File Structure**

```
📁 Download_YouTube_Video_in_Terminal
│
├── YoutubeFixed_Normal.py  # Main TUI + download logic
├── css/
│   └── FinalMain.tcss      # Styling for main UI
└── README.md               # Documentation
```

---

### **📸 Screenshots (Optional Section Placeholder)**

> Add terminal screenshots here showing:

* Main input screen
* Metadata selection table
* Download progress
* Completion screen

---

### **🚀 Roadmap / Future Enhancements**

* [ ] Playlist + Channel downloader UI
* [ ] Merging audio+video automatically (FFmpeg integration)
* [ ] Multi-download queue
* [ ] Save history of downloads

---

### **⚠ Notes**

* This project uses **PyTubeFix**, a fork that maintains compatibility with YouTube’s frequent breaking changes.
* If downloads fail, update:

```bash
pip install --upgrade pytubefix
```



---

If you'd like, I can also provide:

* A **proper Wiki structure**
* A **PyPI packaging setup (`setup.py`, `pyproject.toml`)**
* Screenshots in ASCII style
* A **Logo + Banner**

Just say the word.
