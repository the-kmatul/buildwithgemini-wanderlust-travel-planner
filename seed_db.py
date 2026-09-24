"""Seed Firestore database with travel destinations for Wanderlust AI Travel Concierge.
"""

from google.cloud import firestore

# CRITICAL: Hardcode the GCP Project ID as a string literal (NOT read from env or auth)
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-fc0f977637de"

SAMPLE_DESTINATIONS = [
    {
        "destination_id": "kyoto-japan",
        "name": "Kyoto",
        "country": "Japan",
        "category": "Cultural & Historic",
        "description": "Japan's ancient capital, famous for thousands of classical Buddhist temples, gardens, imperial palaces, Shinto shrines, and traditional wooden houses.",
        "best_season": "Spring (Cherry Blossom) & Autumn (Foliage)",
        "avg_daily_cost_usd": 180,
        "rating": 4.9,
        "highlights": [
            "Fushimi Inari Shrine (Torii Gates)",
            "Arashiyama Bamboo Grove",
            "Kinkaku-ji (Golden Pavilion)",
            "Gion Geisha District"
        ],
        "suggested_activities": [
            {"title": "Morning walk through Fushimi Inari red gates", "duration_hours": 3, "type": "Sightseeing"},
            {"title": "Traditional Tea Ceremony in Gion", "duration_hours": 2, "type": "Cultural"},
            {"title": "Arashiyama Bamboo Forest & Monkey Park", "duration_hours": 4, "type": "Nature"}
        ]
    },
    {
        "destination_id": "santorini-greece",
        "name": "Santorini",
        "country": "Greece",
        "category": "Coastal & Island",
        "description": "A iconic Cycladic island in the Aegean Sea featuring whitewashed cubiform houses clinging to steep volcanic cliffs above a turquoise caldera.",
        "best_season": "Late April to October",
        "avg_daily_cost_usd": 250,
        "rating": 4.8,
        "highlights": [
            "Oia Village Sunset",
            "Fira to Oia Cliffside Hike",
            "Red Beach & Akrotiri Ruins",
            "Volcanic Caldera Boat Tour"
        ],
        "suggested_activities": [
            {"title": "Sunset dinner in Oia overlooking the caldera", "duration_hours": 3, "type": "Dining"},
            {"title": "Catamaran Cruise around the volcanic springs", "duration_hours": 5, "type": "Adventure"},
            {"title": "Wine tasting tour at cliffside wineries", "duration_hours": 3, "type": "Tasting"}
        ]
    },
    {
        "destination_id": "banff-canada",
        "name": "Banff National Park",
        "country": "Canada",
        "category": "Nature & Alpine",
        "description": "Canada's oldest national park in the heart of the Rocky Mountains, showcasing turquoise glacier lakes, snow-capped peaks, and abundant wildlife.",
        "best_season": "June to September (Hiking) & December to March (Skiing)",
        "avg_daily_cost_usd": 210,
        "rating": 4.9,
        "highlights": [
            "Lake Louise & Moraine Lake",
            "Banff Gondola & Sulphur Mountain",
            "Icefields Parkway Scenic Drive",
            "Johnston Canyon Ice/Water Walks"
        ],
        "suggested_activities": [
            {"title": "Canoeing on the turquoise waters of Lake Louise", "duration_hours": 2, "type": "Outdoor"},
            {"title": "Hike to Plain of Six Glaciers Teahouse", "duration_hours": 5, "type": "Hiking"},
            {"title": "Soak in Banff Upper Hot Springs", "duration_hours": 2, "type": "Relaxation"}
        ]
    },
    {
        "destination_id": "serengeti-tanzania",
        "name": "Serengeti National Park",
        "country": "Tanzania",
        "category": "Wildlife & Safari",
        "description": "World-famous wildlife sanctuary known for the annual Great Migration of over 1.5 million wildebeest and zebra across vast savanna plains.",
        "best_season": "June to October (Dry season safari) & January to March (Calving season)",
        "avg_daily_cost_usd": 450,
        "rating": 4.95,
        "highlights": [
            "Great Migration River Crossings",
            "Hot Air Balloon Safari at Sunrise",
            "Ngorongoro Crater Day Excursion",
            "Big Five Game Drives"
        ],
        "suggested_activities": [
            {"title": "Full-day Big Five Safari drive with picnic lunch", "duration_hours": 8, "type": "Safari"},
            {"title": "Sunrise Hot Air Balloon Flight over the plains", "duration_hours": 3, "type": "Visual/Bucket List"},
            {"title": "Maasai Village Cultural Visit", "duration_hours": 2, "type": "Cultural"}
        ]
    },
    {
        "destination_id": "reykjavik-iceland",
        "name": "Reykjavik & Golden Circle",
        "country": "Iceland",
        "category": "Adventure & Geothermal",
        "description": "Gateway to Iceland's dramatic volcanic landscape, geysers, roaring waterfalls, black sand beaches, and the magical Northern Lights.",
        "best_season": "September to March (Northern Lights) & June to August (Midnight Sun)",
        "avg_daily_cost_usd": 220,
        "rating": 4.75,
        "highlights": [
            "Blue Lagoon Geothermal Spa",
            "Golden Circle (Thingvellir, Geysir, Gullfoss)",
            "Reynisfjara Black Sand Beach",
            "Aurora Borealis Hunting Tour"
        ],
        "suggested_activities": [
            {"title": "Tour the Golden Circle waterfalls and erupting geysers", "duration_hours": 7, "type": "Sightseeing"},
            {"title": "Relax in the Blue Lagoon geothermal waters", "duration_hours": 3, "type": "Wellness"},
            {"title": "Night tour searching for the Northern Lights", "duration_hours": 4, "type": "Excursion"}
        ]
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("destinations")

    print("Seeding destinations...")
    for item in SAMPLE_DESTINATIONS:
        doc_id = item["destination_id"]
        collection_ref.document(doc_id).set(item)
        print(f"  ✓ Seeded destination: {item['name']} ({doc_id})")

    print("Seeding complete! Successfully added sample items to Firestore collection 'destinations'.")


if __name__ == "__main__":
    seed_database()
