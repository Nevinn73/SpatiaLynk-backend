from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import QueryRequest
from app.prompt_parser import parse_query
from app.recommender import recommend_places
from app.multilevel import multilevel_recommend

app = FastAPI(
    title="SpatiaLynk Recommendation API",
    description="Spatial-Textual Multi-Level Recommendation System for FYP",
    version="1.0.0"
)

# -------------------------------------------------------
# CORS (Allow Mobile App / Web App to Access Backend)
# -------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- Lock to your domain during production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------

@app.get("/")
def root():
    return {"message": "SpatiaLynk API is running."}


# -------------------------------------------------------
# Endpoint 1 — Parse Query Only (Debugging + UI helpers)
# -------------------------------------------------------

@app.post("/parse-query")
def parse_query_endpoint(req: QueryRequest):
    parsed = parse_query(req.query)
    return {
        "raw_query": req.query,
        "parsed": parsed
    }


# -------------------------------------------------------
# Endpoint 2 — Single-Level Recommendation
# (Basic recommender used earlier)
# -------------------------------------------------------

@app.post("/recommend")
def recommend_endpoint(req: QueryRequest):
    result = recommend_places(req.query)
    return result


# -------------------------------------------------------
# Endpoint 3 — Multi-Level Spatial Recommendation
# (FINAL FYP FUNCTION)
# -------------------------------------------------------

@app.post("/multilevel-recommend")
def multilevel_endpoint(req: QueryRequest):
    result = multilevel_recommend(req.query, top_k=req.top_k)

    # Structure response for mobile:
    return {
        "query": req.query,
        "level": result.get("level"),
        "explanation": result.get("explanation"),
        "parsed": result.get("parsed"),
   	# This part varies depending on level:
        "data": {
            key: result[key] for key in result.keys()
            if key not in ["level", "explanation", "parsed"]
        }
    }
