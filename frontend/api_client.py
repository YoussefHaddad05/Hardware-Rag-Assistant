import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Retrieve the backend URL from the environment
API_BASE_URL = os.getenv("API_BASE_URL")


def query_backend(question: str) -> dict:
    """
    Sends the user's question to the FastAPI backend.

    Returns a dictionary containing either:
    - status="success" with the backend response
    - status="error" with a friendly error message
    """

    if not API_BASE_URL:
        return {
            "status": "error",
            "message": "API_BASE_URL is not configured."
        }

    try:
        # Build the backend endpoint
        endpoint = f"{API_BASE_URL}/query"

        # Send the question to FastAPI
        response = requests.post(
            endpoint,
            json={"question": question},
            timeout=60
        )

        # Raise an exception for HTTP errors
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Validate the expected response structure
        if "answer" in data and "sources" in data:
            return {
                "status": "success",
                "data": data
            }

        return {
            "status": "error",
            "message": "Backend returned an unexpected response format."
        }

    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Failed to connect to the backend. Is FastAPI running?"
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "The backend took too long to respond."
        }

    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "message": f"Backend returned an HTTP error: {e.response.status_code}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"An error occurred while communicating with the backend: {e}"
        }