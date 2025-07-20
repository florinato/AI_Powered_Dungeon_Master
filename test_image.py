from gradio_client import Client

client = Client("taufiqdp/FLUX")
result = client.predict(
		prompt="""--- The Glitchwind Wastes ---
As you crest the final ridge, the Glitchwind Wastes claw at your senses. A symphony of crackling static, punctuated by the groan of warped metal, assaults your ears,
a cacophony that seems to vibrate in your very bones. Twisted factories and skeletal towers loom from the perpetual twilight, their shattered windows spitting out bursts of neon-green energy, while the metallic tang of ozone and burnt circuits hangs heavy in the air,
a chilling perfume of technological decay. The air itself feels thick, heavy with the ghosts of lost data and the phantom echoes of forgotten ambition.""",
		seed=0,
		randomize_seed=True,
		width=1024,
		height=1024,
		guidance_scale=3.5,
		num_inference_steps=28,
		api_name="/infer"
)
print(result)