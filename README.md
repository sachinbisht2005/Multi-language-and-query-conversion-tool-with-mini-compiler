# 🚀 CodeShift — Multi-Language Transpiler

A complete web-based multi-language code transpiler system with modern VS Code-style UI.

---

## 📁 Project Structure

```
transpiler-project/
├── frontend/
│   └── index.html          ← Complete frontend (all 4 modules)
├── backend/
│   ├── app.py              ← Flask REST API
│   ├── requirements.txt    ← Python dependencies
│   └── transpiler/
│       ├── __init__.py
│       └── engine.py       ← Core transpiler logic
└── README.md
```

---

## ✨ Features

### 🔄 Main Transpiler (Backend-powered + Client fallback)
- C → Python
- Python → C
- C++ → Python
- Python → C++
- Supports: variables, loops, conditionals, functions, I/O

### 🗄 SQL → MySQL Converter (Frontend Mock)
- TOP → LIMIT
- ISNULL → IFNULL
- GETDATE → NOW()
- DATEDIFF / DATEADD conversion
- NVARCHAR → VARCHAR
- IDENTITY → AUTO_INCREMENT
- [bracket] → `backtick` quoting
- NOLOCK removal

### 📘 TypeScript → JavaScript (Frontend Mock)
- Remove interface declarations
- Strip type annotations
- Remove generics
- Convert enums to JS objects
- Remove access modifiers (public/private/protected/readonly)
- Remove `as Type` casts

### 🌳 AST Visualizer (Frontend Mock)
- Interactive tree view
- Expand/collapse nodes
- C and Python AST samples
- Copy AST as JSON

---

## ⚙️ Setup Instructions

### Option A: Frontend Only (No backend needed)

1. Open `frontend/index.html` directly in any browser
2. The app runs fully client-side with a built-in JS transpiler engine
3. All 4 modules work without any server

> Note: Client-side transpiler covers most cases. For best accuracy, use the backend.

---

### Option B: Full Stack (Frontend + Backend)

#### 1. Start the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Server runs at: `http://localhost:5000`

Test it:
```bash
curl -X POST http://localhost:5000/convert \
  -H "Content-Type: application/json" \
  -d '{"source_code": "int x = 5;", "source_lang": "c", "target_lang": "python"}'
```

#### 2. Open the Frontend

Simply open `frontend/index.html` in your browser.

The frontend auto-detects the backend. If the backend is unreachable, it falls back to the client-side engine.

---

## 🧠 Compiler Architecture

```
Source Code
     │
     ▼
┌─────────────┐
│  Tokenizer  │  → Breaks code into tokens
└─────────────┘
     │
     ▼
┌─────────────┐
│   Parser    │  → Identifies constructs (loops, functions, etc.)
└─────────────┘
     │
     ▼
┌─────────────┐
│  AST Build  │  → Creates Abstract Syntax Tree
└─────────────┘
     │
     ▼
┌─────────────┐
│ Code Gen    │  → Generates target language code
└─────────────┘
     │
     ▼
Converted Code
```

---

## 🎨 UI Features

- Dark / Light mode toggle
- Monaco-style editor with syntax highlighting (CodeMirror)
- 4 tabbed modules
- Copy & Download buttons
- Sample code loader
- Live status bar
- Toast notifications
- Responsive design (mobile-friendly)
- Keyboard shortcut: Ctrl+Enter to convert

---

## 📡 API Reference

### POST /convert

**Request:**
```json
{
  "source_code": "int x = 5;",
  "source_lang": "c",
  "target_lang": "python"
}
```

**Response:**
```json
{
  "converted_code": "x = 5"
}
```

**Supported language values:** `c`, `cpp`, `python`

### GET /health
Returns API status.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS |
| Editor | CodeMirror 5 |
| Backend | Python 3.8+, Flask |
| CORS | flask-cors |
| Transpiler | Custom rule-based engine |

---

## 📝 Notes for Demo

1. The **client-side fallback** means the app works even without running the backend — great for quick demos
2. The **SQL, TypeScript, and AST** modules are frontend-only — no backend required
3. Use **"Load Sample"** button to quickly populate editor with working examples
4. The **AST Viewer** shows a realistic tree structure — click nodes to expand/collapse

---

Made with ❤️ for college project demo
