# image_generator.py
import io
import os
import re

from gradio_client import Client, file
from PIL import Image


def generate_image_with_gradio(description: str, location_name: str, folder="generated_images") -> dict | None:
    """
    Generates an image using a Gradio client connected to a Hugging Face Space.

    Args:
        description: The text prompt for image generation.
        location_name: The name of the game location, used for the filename.
        folder: The directory to save the generated image.

    Returns:
        A dictionary {'file_path': str} on success, None otherwise.
        Nota: Gradio no devuelve una URL pública, solo el archivo local.
    """
    if not description:
        print("Warning: No description provided for image generation. Skipping.")
        return None

    try:
        # Inicializa el cliente apuntando al espacio de Hugging Face
        print("Connecting to Gradio client for FLUX.1-dev... (This may take a moment)")
        client = Client("black-forest-labs/FLUX.1-dev")
        print("Client connected.")

        # Construye un prompt más efectivo para el modelo
        prompt = f"masterpiece, best quality, ultra-detailed, illustration, fantasy art. {description}"
        
        print(f"Generating image with prompt: '{prompt[:100]}...'")

        # Llama a la función 'predict' del modelo en el espacio de Gradio
        # Los parámetros (width, height, etc.) se pueden ajustar.
        result = client.predict(
            prompt=prompt,
            seed=0,  # Poner 0 y randomize_seed=True es una práctica común para tener variedad
            randomize_seed=True,
            width=1024,
            height=1024,
            guidance_scale=3.5,
            num_inference_steps=28,
            api_name="/infer"
        )
        
        # El resultado suele ser la ruta a un archivo temporal.
        # Necesitamos leer ese archivo y guardarlo permanentemente.
        print(f"Gradio result received: {result}")
        if not result or not os.path.exists(result):
             raise ValueError(f"Gradio client did not return a valid file path. Result: {result}")

        # Crear el directorio de destino si no existe
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created directory: {folder}")

        # Limpiar el nombre de la ubicación para usarlo como nombre de archivo
        safe_location_name = re.sub(r'[^\w\-]+', '_', location_name)
        image_path = os.path.join(folder, f"{safe_location_name}_image.png")
        
        # Copiar el archivo de la ubicación temporal a nuestra ubicación permanente
        # Usamos 'shutil' para una copia robusta de archivos
        import shutil
        shutil.copy(result, image_path)

        print(f"\nSUCCESS! Image for '{location_name}' generated and saved to '{image_path}'")
        
        # Como Gradio no nos da una URL pública, solo devolvemos la ruta local.
        # El campo 'url' será None.
        return {"file_path": image_path, "url": None}

    except Exception as e:
        print(f"An unexpected error occurred during image generation with Gradio: {e}")
        return None


# --- Bloque de Prueba ---
if __name__ == "__main__":
    """
    Este bloque se ejecuta solo cuando el script es llamado directamente.
    Permite probar la función de generación de imágenes de forma aislada.
    """
    print("--- Running Gradio Image Generator Test ---")

    # Definir datos de prueba
    test_description = "A sun-drenched ancient library with floating books and swirling magical energy."
    test_location_name = "The Dragon's Hoard"
    
    print(f"\nTesting with location: '{test_location_name}'")
    print(f"Description: '{test_description}'")
    
    # Llamar a la función
    result_dict = generate_image_with_gradio(test_description, test_location_name)
    
    # Mostrar el resultado
    if result_dict:
        print("\n--- Test Finished Successfully ---")
        print(f"File Path: {result_dict['file_path']}")
        print(f"Image URL: {result_dict['url']} (None as expected with Gradio)")

        # Opcional: intentar abrir la imagen para verificar que es válida
        try:
            from PIL import Image
            img = Image.open(result_dict['file_path'])
            img.show() # Esto abrirá la imagen con el visor de imágenes por defecto de tu SO
            print("Image opened successfully for verification.")
        except Exception as e:
            print(f"Could not open the generated image for verification: {e}")

    else:
        print("\n--- Test Finished with Errors ---")
        print("Image generation failed. Check the logs above for details.")
    
    print("\n--- End of Test ---")