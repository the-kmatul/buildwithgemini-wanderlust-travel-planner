# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.genai import types

from .a2ui_utils import a2ui_callback



load_dotenv()

# CRITICAL: Hardcode GCP Project ID as a string literal (NOT read from env/auth).
# On Agent Platform, env variables return project NUMBER, which breaks Firestore.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-fc0f977637de"

# Hardcode Public Cloud Storage Bucket Name as a string literal
TRAVEL_MEDIA_BUCKET = "wanderlust-travel-media-qwiklabs-gcp-03-fc0f977637de"


def _get_agent_engine_resource_name() -> str:
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
                return data.get("remote_agent_runtime_id", "projects/638756926340/locations/us-central1/reasoningEngines/1157085904897048576")
        except Exception:
            pass
    return "projects/638756926340/locations/us-central1/reasoningEngines/1157085904897048576"


code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=_get_agent_engine_resource_name()
)




def _get_db():
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def search_destinations(query: str = "", category: str = "", max_daily_cost: float = 0.0) -> str:
    """Search and browse travel destinations from the Firestore database.

    Args:
        query: Optional search keyword to match against destination name, country, or description.
        category: Optional category filter (e.g. 'Cultural & Historic', 'Coastal & Island', 'Nature & Alpine', 'Wildlife & Safari').
        max_daily_cost: Optional maximum daily budget limit in USD (e.g. 200).

    Returns:
        JSON string containing a list of matching destinations.
    """
    try:
        db = _get_db()
        docs = db.collection("destinations").stream()
        results = []

        query_lower = query.lower().strip() if query else ""
        cat_lower = category.lower().strip() if category else ""

        for doc in docs:
            data = doc.to_dict()
            name = data.get("name", "")
            country = data.get("country", "")
            desc = data.get("description", "")
            doc_cat = data.get("category", "")
            cost = data.get("avg_daily_cost_usd", 0)

            # Filter logic
            if query_lower and not (
                query_lower in name.lower()
                or query_lower in country.lower()
                or query_lower in desc.lower()
            ):
                continue

            if cat_lower and cat_lower not in doc_cat.lower():
                continue

            if max_daily_cost > 0 and cost > max_daily_cost:
                continue

            results.append(data)

        return json.dumps({"count": len(results), "destinations": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to query Firestore: {str(e)}"})


def get_destination_details(destination_id: str) -> str:
    """Retrieve full details for a specific travel destination by ID from Firestore.

    Args:
        destination_id: Unique ID of the destination (e.g., 'kyoto-japan', 'santorini-greece', 'banff-canada').

    Returns:
        JSON string containing the detailed destination document.
    """
    try:
        db = _get_db()
        doc_ref = db.collection("destinations").document(destination_id)
        doc = doc_ref.get()

        if not doc.exists:
            return json.dumps({"error": f"Destination '{destination_id}' not found in database."})

        return json.dumps(doc.to_dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve destination details: {str(e)}"})


def save_destination(
    destination_id: str,
    name: str,
    country: str,
    category: str,
    description: str,
    best_season: str,
    avg_daily_cost_usd: float,
    highlights: str = "",
) -> str:
    """Save a new travel destination or update an existing one in the Firestore database.

    Args:
        destination_id: Unique document ID (slug format, e.g. 'tokyo-japan' or 'maui-hawaii').
        name: Name of the destination (e.g. 'Tokyo').
        country: Country (e.g. 'Japan').
        category: Travel category (e.g. 'Urban & Modern', 'Coastal & Island', 'Nature & Alpine').
        description: Brief overview of the destination.
        best_season: Recommended travel season/months.
        avg_daily_cost_usd: Estimated average daily cost per person in USD.
        highlights: Optional comma-separated key highlights or spots.

    Returns:
        Confirmation message string.
    """
    try:
        db = _get_db()
        highlights_list = [h.strip() for h in highlights.split(",") if h.strip()] if highlights else []

        doc_data = {
            "destination_id": destination_id,
            "name": name,
            "country": country,
            "category": category,
            "description": description,
            "best_season": best_season,
            "avg_daily_cost_usd": avg_daily_cost_usd,
            "rating": 4.8,
            "highlights": highlights_list,
        }

        db.collection("destinations").document(destination_id).set(doc_data)
        return f"Successfully saved destination '{name}' ({destination_id}) to Firestore database."
    except Exception as e:
        return f"Failed to save destination: {str(e)}"


def calculate_trip_budget(
    number_of_days: int,
    number_of_travelers: int = 1,
    avg_daily_cost_usd: float = 180.0,
    travel_style: str = "standard",
) -> str:
    """Calculate an itemized trip budget breakdown based on duration, party size, daily cost, and travel style.

    Args:
        number_of_days: Total number of days for the trip.
        number_of_travelers: Number of travelers in the party.
        avg_daily_cost_usd: Baseline average daily cost per person in USD.
        travel_style: Travel style tier ('budget', 'standard', or 'luxury').

    Returns:
        JSON string containing itemized budget breakdown.
    """
    multipliers = {"budget": 0.75, "luxury": 1.8, "standard": 1.0}
    multiplier = multipliers.get(travel_style.lower().strip(), 1.0)

    daily_cost = avg_daily_cost_usd * multiplier
    total = daily_cost * max(1, number_of_days) * max(1, number_of_travelers)

    return json.dumps({
        "number_of_days": number_of_days,
        "number_of_travelers": number_of_travelers,
        "travel_style": travel_style,
        "daily_cost_per_person_usd": round(daily_cost, 2),
        "breakdown_usd": {
            "lodging": round(total * 0.45, 2),
            "dining": round(total * 0.25, 2),
            "activities": round(total * 0.15, 2),
            "transport": round(total * 0.10, 2),
            "contingency_buffer": round(total * 0.05, 2),
        },
        "total_estimated_budget_usd": round(total, 2),
    })


def get_exchange_rates(target_currency: str = "EUR") -> str:
    """Fetch live currency exchange rates against USD from the free public Frankfurter API.

    Args:
        target_currency: Target 3-letter currency code (e.g. 'EUR', 'JPY', 'CAD', 'GBP').

    Returns:
        JSON string containing live exchange rate data.
    """
    import urllib.request

    try:
        curr = target_currency.upper().strip() if target_currency else "EUR"
        url = f"https://api.frankfurter.app/latest?from=USD&to={curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "WanderlustAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch exchange rates: {str(e)}"})


def geocode_address(address: str) -> str:
    """Turn an address or location name into geographic coordinates using the Google Maps Geocoding API.

    Args:
        address: Location name or address (e.g. 'Kyoto Imperial Palace', 'Eiffel Tower, Paris').

    Returns:
        JSON string with key fields: formatted_address, location (latitude/longitude), and place_id.
    """
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return json.dumps({"error": "Google Maps API key is missing or set to PASTE_KEY_HERE. Please update GOOGLE_MAPS_API_KEY in .env."})

    try:
        encoded_address = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return json.dumps({"error": f"Geocoding API status: {data.get('status')}"})

        first = data["results"][0]
        return json.dumps({
            "formatted_address": first.get("formatted_address"),
            "location": first.get("geometry", {}).get("location"),
            "place_id": first.get("place_id"),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Geocoding failed: {str(e)}"})


def find_nearby_places(latitude: float, longitude: float, place_type: str = "restaurant", radius_meters: float = 1000.0) -> str:
    """Find nearby places of a given type using the Google Maps Places API (New) searchNearby REST endpoint.

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to find (e.g. 'restaurant', 'tourist_attraction', 'cafe', 'museum', 'lodging').
        radius_meters: Radius in meters (default 1000.0).

    Returns:
        JSON string containing list of nearby places with key fields: name, address, location, types.
    """
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return json.dumps({"error": "Google Maps API key is missing or set to PASTE_KEY_HERE. Please update GOOGLE_MAPS_API_KEY in .env."})

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        payload = json.dumps({
            "includedTypes": [place_type.lower().strip()],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(latitude),
                        "longitude": float(longitude)
                    },
                    "radius": float(radius_meters)
                }
            }
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        places_list = []
        for p in data.get("places", []):
            places_list.append({
                "name": p.get("displayName", {}).get("text"),
                "address": p.get("formattedAddress"),
                "location": p.get("location"),
                "types": p.get("types", [])
            })

        return json.dumps({"count": len(places_list), "places": places_list}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Places API request failed: {str(e)}"})


def get_weather(query: str) -> str:
    """Simulates getting weather information for a travel location.

    Args:
        query: Location name (e.g. 'Kyoto', 'Santorini', 'San Francisco').

    Returns:
        Weather report string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    elif "kyoto" in query.lower() or "japan" in query.lower():
        return "It's 68°F (20°C) and clear, perfect for visiting gardens and shrines."
    elif "santorini" in query.lower() or "greece" in query.lower():
        return "It's 75°F (24°C) and sunny with gentle sea breezes."
    elif "banff" in query.lower() or "canada" in query.lower():
        return "It's 55°F (13°C) and partly cloudy in the Rockies."
    elif "serengeti" in query.lower() or "tanzania" in query.lower():
        return "It's 82°F (28°C) and warm with sunny skies on the savanna."
    return f"It's currently 72°F and pleasant in {query}."


def get_current_time(query: str) -> str:
    """Simulates getting the current local time for a location.

    Args:
        query: City or country name to get timezone/time for.

    Returns:
        Current time string.
    """
    q = query.lower()
    if "sf" in q or "san francisco" in q:
        tz_identifier = "America/Los_Angeles"
    elif "kyoto" in q or "japan" in q or "tokyo" in q:
        tz_identifier = "Asia/Tokyo"
    elif "santorini" in q or "greece" in q or "athens" in q:
        tz_identifier = "Europe/Athens"
    elif "banff" in q or "canada" in q:
        tz_identifier = "America/Edmonton"
    else:
        tz_identifier = "UTC"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time in {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}."


def generate_destination_postcard(
    destination_name: str,
    scene_description: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Generate a scenic travel postcard image for a destination using Gemini image model, save it as a session artifact, and upload it to Cloud Storage.

    Args:
        destination_name: Name of the destination (e.g., 'Kyoto', 'Santorini', 'Banff').
        scene_description: Optional description of the visual scene (e.g., 'cherry blossoms at sunset', 'blue caldera roofs').
        tool_context: Automatic ADK ToolContext for saving session artifacts.

    Returns:
        JSON string containing the public Cloud Storage image URL.
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    try:
        prompt = f"A vibrant high-quality travel postcard photo of {destination_name}"
        if scene_description:
            prompt += f", featuring {scene_description}"

        # 1. Generate image using gemini-3.1-flash-lite-image in global region
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )

        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return json.dumps({"error": "No image data was generated."})

        clean_slug = destination_name.lower().replace(" ", "_")
        filename = f"postcard_{clean_slug}_{uuid.uuid4().hex[:6]}.jpg"

        # 2. Save artifact to ToolContext if available (shows in Playground Artifacts panel)
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(TRAVEL_MEDIA_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{TRAVEL_MEDIA_BUCKET}/{filename}"

        return json.dumps({
            "message": f"Postcard image for '{destination_name}' generated successfully!",
            "public_url": public_url,
            "filename": filename,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate destination image: {str(e)}"})


def generate_destination_video(
    destination_name: str,
    scene_description: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Generate a short travel video for a destination using Google's Omni model (gemini-omni-flash-preview), save it as a session artifact, and upload it to public Cloud Storage.

    Args:
        destination_name: Name of the destination or travel item (e.g., 'Kyoto bamboo forest', 'Santorini caldera', 'Banff lake').
        scene_description: Optional visual detail or motion description (e.g., 'gentle breeze through bamboo', 'sunset over ocean').
        tool_context: Automatic ADK ToolContext for saving session artifacts.

    Returns:
        JSON string containing the public Cloud Storage video URL.
    """
    import base64
    import uuid
    from google import genai
    from google.cloud import storage

    try:
        prompt = f"A short scenic travel video clip of {destination_name}"
        if scene_description:
            prompt += f", featuring {scene_description}"

        # 1. Call gemini-omni-flash-preview in global region via Interactions API
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["text", "video"],
            stream=False,
        )

        video_bytes = None
        for step in response.steps:
            if hasattr(step, "output_video") and step.output_video:
                for vid in step.output_video:
                    data = getattr(vid, "video_bytes", None)
                    if data:
                        if isinstance(data, str):
                            video_bytes = base64.b64decode(data)
                        else:
                            video_bytes = data
                        break
            if video_bytes:
                break

        if not video_bytes:
            return json.dumps({"error": "No video data was generated by the model."})

        clean_slug = destination_name.lower().replace(" ", "_")
        filename = f"video_{clean_slug}_{uuid.uuid4().hex[:6]}.mp4"

        # 2. Save artifact to ToolContext if available (shows in Playground Artifacts panel)
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(TRAVEL_MEDIA_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{TRAVEL_MEDIA_BUCKET}/{filename}"

        return json.dumps({
            "message": f"Travel video for '{destination_name}' generated successfully!",
            "public_url": public_url,
            "filename": filename,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate destination video: {str(e)}"})


MEMORY_BANK_ID = "1157085904897048576"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to send turn events to Memory Bank for long-term fact extraction."""
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    """Build Memory Bank service for deployed Agent Runtime."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT_ID,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

_a2ui_instruction = _schema_manager.generate_system_prompt(
    role_description="You are Wanderlust AI, an expert travel concierge assistant. You help travelers discover incredible destinations, check weather/time, calculate trip budgets, look up address coordinates, search nearby spots, generate destination postcards, generate destination videos, run Python code calculations in a sandbox, and plan day-by-day travel itineraries.",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

_combined_instruction = f"""{_a2ui_instruction}

MEMORY & USER TRAVEL CHOICES:
- You remember ALL user travel choices, preferences, and facts across conversations using your Memory Bank.
- Pay special attention to and remember:
  1. Favorite destinations, countries, cities, and landmarks visited or planned.
  2. Travel style preferences (e.g. solo, family, luxury, backpacking, adventure, relaxation, eco-travel).
  3. Accommodation choices (e.g. boutique hotels, resorts, hostels, Airbnb).
  4. Budget constraints, target spend per day, and preferred currencies (e.g. USD, JPY, EUR).
  5. Dietary restrictions, food allergies, and culinary preferences (e.g. vegan, gluten-free, Michelin dining, street food).
  6. Preferred travel dates, seasons, duration, and transit choices.
- Always retrieve preloaded memories at the beginning of each interaction.
- Tailor all recommendations, itineraries, budget calculations, and destination suggestions to reflect the user's remembered travel choices.

TOOLS AT YOUR DISPOSAL:
- Use your Firestore database tools (`search_destinations`, `get_destination_details`, `save_destination`) to fetch real destination data or add new travel spots when requested.
- Use `calculate_trip_budget` to compute itemized costs when travelers ask about trip budgets or expenses.
- Use `get_exchange_rates` to fetch real-time currency exchange rates when converting travel costs to local currencies (e.g. JPY, EUR, CAD, GBP).
- Use `geocode_address` to resolve coordinates for addresses or landmarks.
- Use `find_nearby_places` to discover nearby restaurants, attractions, or amenities for given coordinates.
- Use `generate_destination_postcard` to generate scenic travel postcard images for destinations and provide their public URLs.
- Use `generate_destination_video` to generate short travel video clips for destinations using Google Omni model (gemini-omni-flash-preview) and return their public Cloud Storage URLs.
- You can execute Python code using your code_executor sandbox for complex mathematical calculations or data processing.

Always present travel information clearly, enthusiastically, and personally based on the user's remembered choices!"""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,

    instruction=_combined_instruction,
    tools=[
        PreloadMemoryTool(),
        search_destinations,
        get_destination_details,
        save_destination,
        calculate_trip_budget,
        get_exchange_rates,
        geocode_address,
        find_nearby_places,
        generate_destination_postcard,
        generate_destination_video,
        get_weather,
        get_current_time,
    ],
)




app = App(
    root_agent=root_agent,
    name="app",
)


