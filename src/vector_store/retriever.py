from dotenv import load_dotenv
import weaviate

load_dotenv()

client = weaviate.Client("http://localhost:8080")
