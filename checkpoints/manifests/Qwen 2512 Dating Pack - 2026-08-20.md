# Qwen 2512 dating-pack external model manifest

These large files are installed locally and intentionally excluded from Git.

| Purpose | Installed path under `C:\projects\AI-Tools\ComfyUI` | Bytes | SHA256 |
| --- | --- | ---: | --- |
| Qwen Image 2512 FP8 base | `models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors` | 20,430,679,144 | `5DC80554D5D83390046A2F4A94ECE06AFB7700BF7B0AAF8BDE9769793875876B` |
| Four-step Lightning LoRA | `models\loras\Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors` | 1,698,951,104 | `AD12117461CB41E2EA637FEC8DF6392CE8E8550C47FBE2B829ED3DEB98262066` |
| Samsung realism LoRA | `models\loras\samsung_qwen2512.safetensors` | 295,146,160 | `8923CBEAD2EE4FC2B2DCE90E6F1C81D51E711FF7A385D522CE9FD2FA785F0E20` |

Sources:

- Qwen Image 2512 Comfy model: `https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI`
- Qwen Image 2512 Lightning: `https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning`
- Samsung Qwen 2512: `https://huggingface.co/Danrisi/Samsung_Qwen2512`

The Samsung file was copied from `C:\Users\Mitch\Downloads\samsung_qwen2512.safetensors`. Its embedded metadata identifies `qwen_image` as the base model family, AI Toolkit 0.7.24, epoch 6, and step 1600. Its hash exactly matches the author's Hugging Face file.
