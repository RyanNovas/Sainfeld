import os
import logging
from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from config import GEMINI_API_KEY
import json
from typing import List
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

def format_scene_with_line_breaks(scene):
    lines = scene.split('\n')
    formatted_lines = []
    
    for line in lines:
        match = re.match(r'^(\w+):(.*)', line.strip())
        if match:
            character = match.group(1).upper()
            dialogue = match.group(2).strip()
            formatted_lines.append(f"{character}\n{dialogue}\n")
        else:
            formatted_lines.append(line + "\n")
    
    return "".join(formatted_lines)

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload_image.html", {"request": request})

@app.post("/upload_image")
async def upload_image(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))
        
        # Ensure the static directory exists
        os.makedirs("static/images", exist_ok=True)
        
        # Save the image to the static directory
        image_path = os.path.join("static/images", image.filename)
        pil_image.save(image_path)
        
        # Set correct permissions for the saved image
        os.chmod(image_path, 0o644)
        
        # Get the URL for the saved image
        image_url = f"/static/images/{image.filename}"
        
        # Generate a Seinfeld scene about the image using Gemini API
        prompt = "Create a short Seinfeld scene (max 150 words) involving Jerry, George, Elaine, and Kramer that revolves around this image. Make sure to reference specific elements from the image in the scene. Format the scene with character names in uppercase followed by a colon, and their dialogue on the next line."
        response = model.generate_content([prompt, pil_image])
        seinfeld_scene = response.text
        
        # Format the scene with line breaks
        formatted_scene = format_scene_with_line_breaks(seinfeld_scene)
        
        logger.info(f"Image {image.filename} uploaded and Seinfeld scene generated successfully")
        logger.info(f"Generated Seinfeld scene: {formatted_scene}")
        
        return JSONResponse({
            "filename": image.filename,
            "format": pil_image.format,
            "size": f"{pil_image.size[0]}x{pil_image.size[1]}",
            "seinfeld_scene": formatted_scene,
            "image_url": image_url
        })
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/develop_scene")
async def develop_scene(
    scene_history: str = Form(...),
    user_input: str = Form(...),
    images: List[UploadFile] = File(None)
):
    try:
        scene_history = json.loads(scene_history)
        
        # Process and save additional images
        new_image_urls = []
        image_contents = []
        if images:
            for image in images:
                image_bytes = await image.read()
                pil_image = Image.open(BytesIO(image_bytes))
                
                # Save the image to the static directory
                image_path = os.path.join("static/images", image.filename)
                pil_image.save(image_path)
                os.chmod(image_path, 0o644)
                
                new_image_urls.append(f"/static/images/{image.filename}")
                image_contents.append(pil_image)

        # Prepare the prompt for scene development
        scene_text = "\n".join([item['content'] for item in scene_history if item['type'] == 'scene'])
        prompt = f"""
        Given the following Seinfeld scene development history:

        {scene_text}

        Continue the scene based on this user input: "{user_input}"
        Format the scene with character names in uppercase followed by a colon, and their dialogue on the next line.
        """
        
        if images:
            prompt += f"\nIncorporate elements from the {len(images)} new image(s) provided into the scene."
            prompt += "\nMaintain the style and tone of Seinfeld, and keep the continuation under 150 words."
        else:
            prompt += "\nMaintain the style and tone of Seinfeld, and keep the continuation under 100 words."

        # Generate the developed scene
        if image_contents:
            response = model.generate_content([prompt] + image_contents)
        else:
            response = model.generate_content(prompt)
        
        developed_scene = response.text
        
        # Format the scene with line breaks
        formatted_scene = format_scene_with_line_breaks(developed_scene)
        
        logger.info(f"Scene developed successfully")
        logger.info(f"Developed scene: {formatted_scene}")
        
        return JSONResponse({
            "developed_scene": formatted_scene,
            "new_image_urls": new_image_urls
        })
    except Exception as e:
        logger.error(f"Error developing scene: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))