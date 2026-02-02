import os, re
import google.generativeai as genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    "models/gemini-flash-latest",
    generation_config={
        "temperature": 0.0,
        "max_output_tokens": 4096,
    }
)


PROMPT = """
You are given a photo of a shopping receipt.

Read all visible text from the image.
Extract receipt information.

Return VALID JSON only.

Schema:
{
  "store_name": string | null,
  "total": number | null,
  "items": [
    {"id": number, "name": string, "amount": number}
  ]
}
"""


import io
import json
from PIL import Image
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def parse_receipt(request):
    try:
        # 1. Validasi method
        if request.method != "POST":
            return JsonResponse(
                {"error": "POST method required"},
                status=405
            )

        # 2. Validasi file image
        if "image" not in request.FILES:
            return JsonResponse(
                {"error": "image file is required"},
                status=400
            )

        # 3. Ambil image dari request
        image_file = request.FILES["image"]
        image_bytes = image_file.read()

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception:
            return JsonResponse(
                {"error": "Invalid image file"},
                status=400
            )

        # 4. Kirim prompt + image ke Gemini
        response = model.generate_content([
            PROMPT,
            image,
        ])

        # 5. Ambil text response (SDK lama: multipart safe)
        texts = [
            part.text
            for c in response.candidates
            for part in c.content.parts
            if hasattr(part, "text")
        ]

        text = "".join(texts).strip()
        print("RAW AI TEXT:", repr(text))

        json_str = extract_json(text)
        if not json_str:
            return JsonResponse(
                {"error": "AI response does not contain JSON", "raw": text},
                status=500
            )

        return JsonResponse(json.loads(json_str), safe=False)

    except json.JSONDecodeError as e:
        return JsonResponse(
            {
                "error": "JSON decode failed",
                "detail": str(e),
                "raw": text if "text" in locals() else None
            },
            status=500
        )

    except Exception as e:
        return JsonResponse(
            {"error": "Internal error", "detail": str(e)},
            status=500
        )


# ambil konten di antara ```json ... ``` ATAU fallback ke {...}
def extract_json(text: str) -> str | None:
    # case 1: fenced code block
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1)

    # case 2: raw json
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]

    return None

@api_view(["POST"])
def generate_insight(request):
    prompt = request.data.get("prompt")

    if not prompt:
        return Response(
            {"error": "Prompt is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return Response({"insight": text})
    except Exception:
        return Response(
            {"error": "AI service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

