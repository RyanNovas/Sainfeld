import os
import logging
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from config import GEMINI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload_image.html", {"request": request})

@app.post("/upload_image")
async def upload_image(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))
        
        # Ensure the static directory exists
        os.makedirs("static", exist_ok=True)
        
        # Save the image to the static directory
        image_path = os.path.join("static", image.filename)
        pil_image.save(image_path)
        
        # Set correct permissions for the saved image
        os.chmod(image_path, 0o644)
        
        # Get the URL for the saved image
        image_url = f"/static/{image.filename}"
        
        # Generate a Seinfeld scene about the image using Gemini API
        prompt = "Create a short Seinfeld scene (max 150 words) involving Jerry, George, Elaine, and Kramer that revolves around this image. Make sure to reference specific elements from the image in the scene."
        response = model.generate_content([prompt, pil_image])
        seinfeld_scene = response.text
        
        logger.info(f"Image {image.filename} uploaded and Seinfeld scene generated successfully")
        logger.info(f"Generated Seinfeld scene: {seinfeld_scene}")
        
        return JSONResponse({
            "filename": image.filename,
            "format": pil_image.format,
            "size": f"{pil_image.size[0]}x{pil_image.size[1]}",
            "seinfeld_scene": seinfeld_scene,
            "image_url": image_url
        })
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))