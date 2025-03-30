from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import pandas as pd
import zipfile
import io
import requests
import json

AIPROXY_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjMwMDI2NjdAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.AgYk2mGdpTld9BgmwdYFhcbidyUfm8-iSkQi6Uhj_F0"
AI_PROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

app = FastAPI()

@app.post("/api/")
async def answer_question(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    extracted_data = ""

    if file and file.filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(await file.read()), "r") as zip_ref:
                csv_files = [f for f in zip_ref.namelist() if f.endswith(".csv")]
                if not csv_files:
                    raise HTTPException(status_code=400, detail="No CSV file found in ZIP.")

                csv_data_list = []
                for csv_file in csv_files:
                    with zip_ref.open(csv_file) as f:
                        df = pd.read_csv(f)
                        csv_data_list.append(df.to_csv(index=False))

                extracted_data = "\n\n".join(csv_data_list)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing ZIP file: {str(e)}")

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIPROXY_TOKEN}"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert AI assistant designed to solve graded assignment questions "
                        "from the IIT Madras Data Science online degree program. "
                        "Your task is to accurately answer questions based on the provided text or data. "
                        "If a CSV file is given, analyze the data within it to find the answer. "
                        "If no CSV file is provided, use your general knowledge and reasoning abilities to answer the question. "
                        "Give only the answer to directly submit it."
                    )
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nCSV Data:\n{extracted_data}"
                }
            ]
        }
        response = requests.post(AI_PROXY_URL, headers=headers, json=data)
        response_json = response.json()

        if "choices" not in response_json or not response_json["choices"]:
            raise HTTPException(status_code=500, detail="Invalid response from AI Proxy API.")

        ai_response = response_json["choices"][0]["message"]["content"].strip()
        ai_response = ai_response.replace("json", "").replace("", "").strip()

        try:
            ai_response = json.loads(ai_response)
            return {"answer": json.dumps(ai_response, separators=(",", ":"))}
        except json.JSONDecodeError:
            return {"answer": ai_response}

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"AI Proxy API error: {str(e)}") 

