from fastapi import APIRouter, BackgroundTasks, HTTPException
import asyncio

router = APIRouter()

# ModelLoader class for lazy model loading
class ModelLoader:
    def __init__(self):
        self.model = None
        self.loading = False
        self.loaded = False

    async def load_model(self):
        if self.loaded:
            return self.model
        if self.loading:
            while self.loading:
                await asyncio.sleep(0.1)
            return self.model
        self.loading = True
        try:
            print("🤖 Loading AI model...")
            # Replace the following sleep with your model loading code
            await asyncio.sleep(2)
            # Example:
            # from sentence_transformers import SentenceTransformer
            # self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.model = "AI Model Loaded"  # Replace with your actual model
            self.loaded = True
            print("✅ AI model loaded successfully!")
            return self.model
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise HTTPException(status_code=500, detail=f"Model loading failed: {str(e)}")
        finally:
            self.loading = False

# Global model loader instance
model_loader = ModelLoader()

@router.get("/model/status")
async def get_model_status():
    """
    Endpoint to get current model loading status.
    """
    return {
        "loaded": model_loader.loaded,
        "loading": model_loader.loading,
        "status": "loaded" if model_loader.loaded else "loading" if model_loader.loading else "not_loaded"
    }

@router.post("/model/preload")
async def preload_model(background_tasks: BackgroundTasks):
    """
    Endpoint to start model loading in the background if not already loaded.
    """
    if model_loader.loaded:
        return {"status": "already_loaded"}
    if model_loader.loading:
        return {"status": "loading"}

    background_tasks.add_task(model_loader.load_model)
    return {"status": "loading_started"}
