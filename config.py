import os
from dotenv import load_dotenv
import motor.motor_asyncio
from openai import OpenAI

load_dotenv()

# MongoDB configuration — V2 uses separate database
MONGO_URI = os.getenv("MONGO_URI")
clientdb = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = clientdb.cv_builder_v2
user_profiles_collection = db.get_collection("user_profiles")
generated_cvs_collection = db.get_collection("generated_cvs")

# AI client (NVIDIA)
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("AI_API_KEY"),
)

# Razorpay
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

# Free tier limits
FREE_FIELD_LIMIT = 2       # Max number of distinct field types a free user can use
FREE_TAILOR_CREDITS = 4    # Total AI tailor credits for free users
