import re

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

LANGUAGES = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C",
    "C++",
    "C#",
    "Go",
    "Rust",
    "PHP",
    "Ruby",
    "Swift",
    "Kotlin",
    "SQL",
]

def _result(
    category,
    title,
    explanation,
    cause,
    solution,
    example,
    confidence="Likely match",
    followups=None,
):
    return {
        "category": category,
        "title": title,
        "explanation": explanation,
        "cause": cause,
        "solution": solution,
        "example": example,
        "confidence": confidence,
        "followups": followups or [
            {
                "question": "How do I find the exact line that caused this?",
                "answer": "Start at the first error in the output, then find the first stack-trace frame that points to your own code. Inspect that line and the values it uses.",
            },
            {
                "question": "What should I share if I need more help?",
                "answer": "Include the complete error text, the language and runtime version, and the smallest code sample that still reproduces the issue. Remove secrets first.",
            },
        ],
    }


def analyze_error(error_text, language, mode="rule"):
    text = error_text.strip()
    lowered = text.lower()

    if mode == "general":
        return _result(
            "General guidance",
            "Start with the first reported location",
            f"This {language} diagnostic says the program could not continue as written. Read the first reported error and trace the values used on that line.",
            "Common causes include a misspelled identifier, an unexpected value type, a missing dependency, or a syntax issue near the reported line.",
            "Open the referenced file and line, inspect the values or syntax immediately around it, and address the first error before later messages.",
            "// Check the reported line and nearby values.\n// Compare actual values and types with what the operation expects.",
            confidence="General guidance",
        )

    if "indexerror" in lowered or "index out of range" in lowered or "arrayindexoutofbounds" in lowered:
        return _result(
            "IndexError",
            "An index points past the end of a collection",
            "The code requested an item at a position that does not exist. Since indexes usually start at zero, the last valid position is one less than the collection length.",
            "The index may be off by one, or the collection may be empty or shorter than expected.",
            "Check the collection length before indexing. For loops, use a condition that stops before the length, and handle the empty-collection case.",
            "if items and index < len(items):\n    value = items[index]",
            followups=[
                {
                    "question": "Why does my loop go one step too far?",
                    "answer": "This is usually an off-by-one condition. Use `index < len(items)`, not `index <= len(items)`, because the length itself is not a valid index.",
                },
                {
                    "question": "What if the collection is empty?",
                    "answer": "Check whether it contains any items before accessing index zero. An empty collection has no valid indexes.",
                },
            ],
        )

    if language == "Python":
        match = re.search(r"name ['\"]([^'\"]+)['\"] is not defined", text, re.I)
        if match or "nameerror" in lowered:
            name = match.group(1) if match else "the referenced name"
            return _result(
                "NameError",
                f"{name} has not been defined",
                f"Python reached `{name}` but could not find a variable, function, or import with that name in the current scope.",
                "The name may be misspelled, assigned only inside another scope, or used before its definition. Imports can also be missing.",
                f"Check the spelling and capitalization of `{name}`, define it before this line, or import it from the module that owns it.",
                f"{name} = ...  # define or import this before it is used\nprint({name})",
            )

        if "modulenotfounderror" in lowered or "no module named" in lowered:
            match = re.search(r"No module named ['\"]?([^'\"\s]+)", text, re.I)
            module = match.group(1) if match else "the missing package"
            return _result(
                "Import error",
                f"Python cannot find `{module}`",
                f"The active Python environment does not have an importable module named `{module}`.",
                "The package may not be installed in this environment, the import name may differ from its package name, or the wrong interpreter may be selected.",
                f"Install the package in the environment running your program, then confirm your editor and terminal use that same interpreter. For example: `python -m pip install {module}`.",
                f"python -m pip install {module}\npython -c \"import {module}\"",
            )

        if "indentationerror" in lowered or "taberror" in lowered:
            return _result(
                "IndentationError",
                "The block indentation is inconsistent",
                "Python uses indentation to decide which statements belong to a block, so whitespace is part of the program structure.",
                "A line is likely indented at the wrong level, or tabs and spaces have been mixed within the same block.",
                "Align the affected line with its surrounding block and use spaces consistently. In most Python projects, four spaces per level is the convention.",
                "if ready:\n    run_task()  # one consistent indentation level",
            )

        if "typeerror" in lowered and ("unsupported operand" in lowered or "not supported between" in lowered):
            return _result(
                "TypeError",
                "An operation received incompatible types",
                "Python does not define this operation for the types of values on both sides of the expression.",
                "A value may have a different type than expected, such as a number represented as text or a missing value used in arithmetic.",
                "Inspect both values with `type(value)`. Convert them when that matches the intent, or correct the earlier code that produced the unexpected type.",
                "count = int(raw_count)  # convert only when the input is meant to be numeric\ntotal = count + 1",
            )

    if language in {"JavaScript", "TypeScript"}:
        match = re.search(r"([\w$]+) is not defined", text, re.I)
        if match or "referenceerror" in lowered:
            name = match.group(1) if match else "the referenced name"
            return _result(
                "ReferenceError",
                f"{name} is not available here",
                f"JavaScript reached `{name}` but no binding with that name is available in the current scope.",
                "The name may be misspelled, declared in a different scope, or used before its module or script has loaded.",
                f"Check the spelling and scope of `{name}`. Declare it before use, or import/export it from the module where it is defined.",
                f"const {name} = ...; // declare or import before use\nconsole.log({name});",
            )

        if "cannot read properties of undefined" in lowered or "cannot read properties of null" in lowered or "cannot read property" in lowered:
            match = re.search(r"reading ['\"]([^'\"]+)['\"]", text, re.I)
            prop = match.group(1) if match else "the property"
            return _result(
                "TypeError",
                f"Cannot read `{prop}` from a missing value",
                f"The value before `.{prop}` is `undefined` or `null` when this code runs.",
                "The value may not have loaded yet, the lookup may have returned no result, or the property path may be incorrect.",
                "Trace the value immediately before this access. Handle the missing case or wait until the data is available before reading its property.",
                f"if (record != null) {{\n  console.log(record.{prop});\n}}",
            )

    return _result(
        "Runtime or compile error",
        "Start with the first reported location",
        f"This {language} diagnostic reports that the program could not continue as written. The exact rule depends on the compiler or runtime that produced it.",
        "Common causes include a misspelled identifier, an unexpected value type, a missing dependency, or a syntax issue near the reported line.",
        "Read the first error in the output, open the referenced file and line, and inspect the values or syntax immediately around it. Later errors may be consequences of the first one.",
        "// Check the reported line and nearby values.\n// Compare the actual value/type with what this operation expects.",
        confidence="General guidance",
    )


@app.get("/")
def index():
    return render_template("index.html", languages=LANGUAGES)


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    error_text = payload.get("error", "")
    language = payload.get("language", "")
    mode = payload.get("mode", "rule")

    if not isinstance(error_text, str) or not error_text.strip():
        return jsonify({"error": "Paste an error message or traceback to get an explanation."}), 400
    if len(error_text) > 12000:
        return jsonify({"error": "Keep the error under 12,000 characters."}), 413
    if language not in LANGUAGES:
        return jsonify({"error": "Choose a supported programming language."}), 400
    if mode not in {"rule", "general"}:
        return jsonify({"error": "Choose a supported analysis mode."}), 400

    return jsonify(analyze_error(error_text, language, mode))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
