# game/image_generator.py

import os
import random
import re
import shutil

from gradio_client import Client
from PIL import Image


def generate_image_with_gradio(
    description: str,
    location_name: str,
    world_id: str,
    world_theme: str,
    historical_context: str | None = None,
    inhabitant_description: str | None = None
) -> str | None:
    """
    Genera una imagen usando un cliente de Gradio.
    Construye un prompt dinámico y contextualizado basado en la definición del mundo
    para asegurar la coherencia temática e histórica.
    """
    if not description:
        print("Warning: No description provided for image generation. Skipping.")
        return None

    try:
        print("Connecting to Gradio client for taufiqdp/FLUX...")
        client = Client("taufiqdp/FLUX")
        print("Client connected.")

        # --- CONSTRUCCIÓN DEL PROMPT 100% DINÁMICO ---

        # 1. Palabras clave de estilo artístico base.
        #    (Estilo de dibujo en blanco y negro que acordamos).
        style_keywords = "black and white ink wash drawing, style of historical etchings, high contrast, chiaroscuro"

        # 2. Contexto del mundo (histórico o temático).
        if historical_context:
            context_prompt = f"a scene from {historical_context}"
        else:
            context_prompt = f"a scene from a world of {world_theme}"

        # 3. Descripción de los habitantes (La pieza clave que se perdió).
        #    Se añade solo si está definida en el manifiesto.
        character_prompt = ""
        if inhabitant_description:
            character_prompt = f"The scene can feature people, such as: {inhabitant_description}."

        # 4. Descripción del lugar específico.
        location_prompt = f"The view shows '{location_name.replace('_', ' ')}', which is described as: {description}"

        # 5. Ensamblaje final del prompt.
        prompt = f"{style_keywords}. {context_prompt}. {character_prompt} {location_prompt}"

        print(f"\n--- Generating Image ---")
        print(f"PROMPT: {prompt[:150]}...")
        print("------------------------")

        # 6. Llamada a la API de Gradio.
        result = client.predict(
            prompt=prompt,
            seed=random.randint(0, 2**32 - 1),
            randomize_seed=False,
            width=1024,
            height=1024,
            guidance_scale=4.5,
            num_inference_steps=30,
            api_name="/infer"
        )
        
        image_filepath = result[0]
        if not image_filepath or not os.path.exists(image_filepath):
             raise ValueError("Gradio client did not return a valid file path.")

        # 7. Organización de carpetas y guardado.
        output_folder = os.path.join("generated_images", world_id)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        safe_location_name = re.sub(r'[^\w\-]+', '_', location_name)
        image_path = os.path.join(output_folder, f"{safe_location_name}.png")
        
        shutil.copy(image_filepath, image_path)

        print(f"\nSUCCESS! Image for '{location_name}' generated and saved to '{image_path}'")
        
        return image_path

    except Exception as e:
        print(f"An unexpected error occurred during image generation with Gradio: {e}")
        return None