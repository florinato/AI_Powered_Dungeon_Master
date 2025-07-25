# image_generator.py

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
    historical_context: str | None = None
) -> str | None:
    """
    Genera una imagen usando un cliente de Gradio, enriqueciendo el prompt
    con el tema, contexto histórico y restricciones de estilo.
    """
    if not description:
        print("Warning: No description provided for image generation. Skipping.")
        return None

    try:
        print("Connecting to Gradio client for taufiqdp/FLUX...")
        client = Client("taufiqdp/FLUX")
        print("Client connected.")

        # --- CONSTRUCCIÓN DEL PROMPT MEJORADO Y ESTRUCTURADO ---

        # 1. Palabras clave de estilo base para alta calidad
        style_keywords = """black and white drawing, high contrast, dramatic chiaroscuro lighting, 
                            ink wash and charcoal style, masterpiece, ultra-detailed, sketch"""

        # 2. El contexto histórico y temático define el "estilo" principal
        if historical_context:
            context_prompt = f"historical illustration of {historical_context}"
        else:
            context_prompt = f"{world_theme} art"

        # 3. La descripción específica de la localización
        location_prompt = f"the interior of '{location_name.replace('_', ' ')}', {description}"
        
        # --- NUEVO: RESTRICCIONES DENTRO DEL PROMPT ---
        # En lugar de un prompt negativo, integramos las exclusiones aquí.
        # Le decimos explícitamente que evite elementos anacrónicos.
        restrictions = "NO modern technology, NO plastic, NO electric lights, NO modern clothing."

        # 4. Combinamos todo en un prompt final y potente.
        prompt = f"{style_keywords}, {context_prompt}. {location_prompt}. {restrictions}"

        print(f"\n--- Generating Image ---")
        print(f"PROMPT: {prompt[:150]}...")
        print("------------------------")

        # 5. Llamar a la API de Gradio SIN el parámetro `negative_prompt`
        result = client.predict(
            prompt=prompt,
            seed=random.randint(0, 2**32 - 1),
            randomize_seed=False,
            width=1024,
            height=1024,
            guidance_scale=4.0,
            num_inference_steps=30,
            api_name="/infer"
        )
        
        image_filepath = result[0]
        print(f"Gradio result received: {image_filepath}")
        if not image_filepath or not os.path.exists(image_filepath):
             raise ValueError("Gradio client did not return a valid file path.")

        # Organización de carpetas y guardado
        output_folder = os.path.join("generated_images", world_id)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created directory: {output_folder}")

        safe_location_name = re.sub(r'[^\w\-]+', '_', location_name)
        image_path = os.path.join(output_folder, f"{safe_location_name}.png")
        
        shutil.copy(image_filepath, image_path)

        print(f"\nSUCCESS! Image for '{location_name}' generated and saved to '{image_path}'")
        
        return image_path

    except Exception as e:
        print(f"An unexpected error occurred during image generation with Gradio: {e}")
        return None