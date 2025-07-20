# image_generator.py

import io
import os
import random
import re
import shutil

from gradio_client import Client
from PIL import Image


# --- FUNCIÓN MODIFICADA ---
def generate_image_with_gradio(
    description: str, 
    location_name: str, 
    world_theme: str, # <--- AÑADIMOS EL TEMA DEL MUNDO
    folder="generated_images"
) -> str | None: # <-- Cambiado para devolver solo la ruta del archivo o None
    """
    Genera una imagen usando un cliente de Gradio, enriqueciendo el prompt
    con el tema general del mundo.

    Args:
        description: La descripción específica de la localización.
        location_name: El nombre de la localización, para el prompt y el nombre de archivo.
        world_theme: El tema general del mundo (ej: 'Cine negro', 'Alta fantasía').
        folder: El directorio donde se guardarán las imágenes.

    Returns:
        La ruta al archivo de imagen guardado en caso de éxito, o None si falla.
    """
    if not description:
        print("Warning: No description provided for image generation. Skipping.")
        return None

    try:
        # Conectar al cliente de Gradio
        print("Connecting to Gradio client for taufiqdp/FLUX...")
        client = Client("taufiqdp/FLUX")
        print("Client connected.")

        # --- CONSTRUCCIÓN DEL PROMPT CONTEXTUALIZADO ---
        # 1. Palabras clave de estilo base para alta calidad.
        style_keywords = "masterpiece, best quality, ultra-detailed, cinematic lighting, atmospheric"
        
        # 2. El tema del mundo actúa como un "filtro" general.
        #    Lo ponemos primero para que guíe todo el proceso.
        #    Ej: "Hardboiled detective film noir art..."
        theme_prompt = f"{world_theme} art"

        # 3. La descripción específica de la localización.
        #    Ej: "...illustration of The Albatross Lounge, a haze of cigarette smoke..."
        location_prompt = f"illustration of {location_name.replace('_', ' ')}, {description}"
        
        # 4. Combinamos todo en un prompt final y potente.
        prompt = f"{style_keywords}, {theme_prompt}. {location_prompt}"
        
        print(f"Generating image with enhanced prompt: '{prompt[:120]}...'")

        # Llamar a la API de Gradio
        result = client.predict(
            prompt=prompt,
            seed=0,
            randomize_seed=True,
            width=1024,
            height=1024,
            guidance_scale=3.5,
            num_inference_steps=28,
            api_name="/infer"
        )
        
        image_filepath = result[0]
        print(f"Gradio result received: {image_filepath}")
        if not image_filepath or not os.path.exists(image_filepath):
             raise ValueError(f"Gradio client did not return a valid file path.")

        # Crear directorio y guardar la imagen
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        safe_location_name = re.sub(r'[^\w\-]+', '_', location_name)
        image_path = os.path.join(folder, f"{safe_location_name}_image_{random.randint(100,999)}.png")
        
        shutil.copy(image_filepath, image_path)

        print(f"\nSUCCESS! Image for '{location_name}' generated and saved to '{image_path}'")
        
        return image_path # Devolvemos solo la ruta, es más simple y útil.

    except Exception as e:
        print(f"An unexpected error occurred during image generation with Gradio: {e}")
        return None


# --- Bloque de Prueba (opcional, para ejecutar el script directamente) ---
if __name__ == "__main__":
    print("--- Running Gradio Image Generator Test (taufiqdp/FLUX) ---")

    test_description = "A forgotten, moss-covered stone altar in the middle of a dark, enchanted forest. Eerie magical light emanates from the cracks in the stone."
    test_location_name = "The Whispering Altar"
    
    print(f"\nTesting with location: '{test_location_name}'")
    print(f"Description: '{test_description}'")
    
    result_dict = generate_image_with_gradio(test_description, test_location_name)
    
    if result_dict:
        print("\n--- Test Finished Successfully ---")
        print(f"File Path: {result_dict['file_path']}")
        try:
            img = Image.open(result_dict['file_path'])
            img.show()
            print("Image opened successfully for verification.")
        except Exception as e:
            print(f"Could not open the generated image for verification: {e}")
    else:
        print("\n--- Test Finished with Errors ---")
        print("Image generation failed. Check the logs above for details.")