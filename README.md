# ErrorBruh

A small Flask-backed error explainer. Paste a compiler/runtime message, choose its language, and get a plain-language explanation, likely cause, and suggested next step.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The analyzer uses deterministic rules for a small set of common errors and general debugging guidance for unmatched messages. It does not call an AI service. Error submissions are analyzed by the Flask app and are not saved on the server.
