from __future__ import annotations

import json

from .aitk_integration import (
    AIToolkitClient,
    build_zimage_job_config,
    choose_completed_lora,
    fingerprint_dataset,
    load_settings,
    publish_lora,
    publish_lora_idempotent,
    validate_dataset,
    validate_generated_dataset,
)
from .social_pack import AIToolkitGenerateNinePhotos
from .social_workbench import (
    AIToolkitSocialPackDrafts,
    AIToolkitSocialPackFinals,
    AIToolkitSocialPackSettings,
    AIToolkitSocialScene,
)
from .identity_lock import AIToolkitIdentityLockSettings, AIToolkitQwenIdentityLock


CATEGORY = "training/AI-Toolkit"


class AIToolkitTrainGeneratedDataset:
    """One-click idempotent manager for the fixed generated dataset."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("job_id", "status", "step", "total_steps", "info", "comfy_lora_name", "details_json")
    FUNCTION = "manage"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    def manage(self):
        settings = load_settings()
        dataset = validate_generated_dataset(settings)
        fingerprint = fingerprint_dataset(dataset)
        job_ref = f"comfy-generated-dataset:{fingerprint}"
        job_name = f"{dataset.trigger_word.replace('_', '-')}-zimage-{fingerprint[:12]}"
        client = AIToolkitClient(settings)
        job = client.find_by_ref(job_ref)
        action = "existing"
        lora_name = ""

        if job is None:
            config = build_zimage_job_config(
                settings,
                job_name=job_name,
                dataset=dataset,
                trigger_word=dataset.trigger_word,
                steps=3000,
                learning_rate=0.0001,
                rank=16,
                save_every=250,
            )
            job = client.submit(job_name, "0", config, job_ref=job_ref)
            action = "submitted"
        elif str(job.get("status", "")).lower() == "completed":
            source = choose_completed_lora(job, client.files(str(job["id"])))
            _, lora_name, copied = publish_lora_idempotent(settings, source)
            action = "published" if copied else "already_published"

        status = str(job.get("status", "unknown"))
        info = str(job.get("info") or "")
        if action == "submitted":
            info = f"Submitted 3,000-step Z-Image Base training. {info}".strip()
        elif action == "published":
            info = f"Training completed and LoRA published as {lora_name}."
        elif action == "already_published":
            info = f"Training completed; identical LoRA already published as {lora_name}."

        details = {
            "action": action,
            "dataset": dataset.summary(),
            "dataset_fingerprint": fingerprint,
            "trigger_word": dataset.trigger_word,
            "training_defaults": {
                "model": settings["z_image_model"],
                "steps": 3000,
                "rank": 16,
                "learning_rate": 0.0001,
                "save_every": 250,
            },
            "job": job,
            "comfy_lora_name": lora_name,
        }
        step = int(job.get("step") or 0)
        total_steps = int(job.get("total_steps") or 3000)
        visible_status = (
            f"{status.upper()} | {job_name}\n"
            f"Step {step:,} / {total_steps:,}\n"
            f"{info or 'AI-Toolkit job is active.'}"
        )
        if lora_name:
            visible_status += f"\nLoRA: {lora_name}"
        result = (
            str(job["id"]),
            status,
            step,
            total_steps,
            info,
            lora_name,
            json.dumps(details, indent=2, default=str),
        )
        return {"ui": {"text": (visible_status,)}, "result": result}


class AIToolkitSubmitZImageTraining:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataset_path": ("STRING", {"default": "C:\\path\\to\\paired-dataset"}),
                "trigger_word": ("STRING", {"default": "my_person"}),
                "job_name": ("STRING", {"default": "my-person-zimage-v1"}),
                "steps": ("INT", {"default": 1000, "min": 1, "max": 100000}),
                "learning_rate": ("FLOAT", {"default": 0.0001, "min": 0.0000001, "max": 1.0, "step": 0.00001}),
                "rank": ("INT", {"default": 16, "min": 1, "max": 512}),
                "save_every": ("INT", {"default": 250, "min": 1, "max": 100000}),
                "gpu_ids": ("STRING", {"default": "0"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("job_id", "status", "details_json")
    FUNCTION = "submit"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    def submit(self, dataset_path, trigger_word, job_name, steps, learning_rate, rank, save_every, gpu_ids):
        settings = load_settings()
        dataset = validate_dataset(dataset_path, trigger_word)
        config = build_zimage_job_config(
            settings,
            job_name=job_name.strip(),
            dataset=dataset,
            trigger_word=trigger_word,
            steps=steps,
            learning_rate=learning_rate,
            rank=rank,
            save_every=save_every,
        )
        job = AIToolkitClient(settings).submit(job_name.strip(), gpu_ids.strip(), config)
        details = {"dataset": dataset.summary(), "job": job}
        return (str(job["id"]), str(job.get("status", "queued")), json.dumps(details, indent=2, default=str))


class AIToolkitTrainingStatus:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"job_id": ("STRING", {"default": ""})}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("status", "step", "total_steps", "info", "log_tail", "details_json")
    FUNCTION = "status"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    def status(self, job_id):
        client = AIToolkitClient(load_settings())
        job = client.status(job_id)
        log_tail = client.log_tail(job_id)
        return (
            str(job.get("status", "unknown")),
            int(job.get("step") or 0),
            int(job.get("total_steps") or 0),
            str(job.get("info") or ""),
            log_tail,
            json.dumps(job, indent=2, default=str),
        )


class AIToolkitPublishCompletedLoRA:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "job_id": ("STRING", {"default": ""}),
                "destination_name": ("STRING", {"default": ""}),
                "overwrite": ("BOOLEAN", {"default": False}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("absolute_path", "comfy_lora_name")
    FUNCTION = "publish"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    def publish(self, job_id, destination_name, overwrite):
        settings = load_settings()
        client = AIToolkitClient(settings)
        job = client.status(job_id)
        source = choose_completed_lora(job, client.files(job_id))
        destination, relative_name = publish_lora(settings, source, destination_name, overwrite)
        return (str(destination), relative_name)


NODE_CLASS_MAPPINGS = {
    "AIToolkitGenerateNinePhotos": AIToolkitGenerateNinePhotos,
    "AIToolkitSocialPackSettings": AIToolkitSocialPackSettings,
    "AIToolkitSocialScene": AIToolkitSocialScene,
    "AIToolkitSocialPackDrafts": AIToolkitSocialPackDrafts,
    "AIToolkitSocialPackFinals": AIToolkitSocialPackFinals,
    "AIToolkitIdentityLockSettings": AIToolkitIdentityLockSettings,
    "AIToolkitQwenIdentityLock": AIToolkitQwenIdentityLock,
    "AIToolkitTrainGeneratedDataset": AIToolkitTrainGeneratedDataset,
    "AIToolkitSubmitZImageTraining": AIToolkitSubmitZImageTraining,
    "AIToolkitTrainingStatus": AIToolkitTrainingStatus,
    "AIToolkitPublishCompletedLoRA": AIToolkitPublishCompletedLoRA,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AIToolkitGenerateNinePhotos": "AI-Toolkit: Generate 9 Social Photos",
    "AIToolkitSocialPackSettings": "Social Pack: Global Settings",
    "AIToolkitSocialScene": "Social Pack: Editable Scene",
    "AIToolkitSocialPackDrafts": "STAGE 1: Generate Drafts",
    "AIToolkitSocialPackFinals": "STAGE 2: Render Finals",
    "AIToolkitIdentityLockSettings": "STAGE 3: Identity Lock Settings",
    "AIToolkitQwenIdentityLock": "STAGE 3: Qwen Identity Lock",
    "AIToolkitTrainGeneratedDataset": "AI-Toolkit: Train Generated Dataset",
    "AIToolkitSubmitZImageTraining": "AI-Toolkit: Submit Z-Image Training",
    "AIToolkitTrainingStatus": "AI-Toolkit: Training Status",
    "AIToolkitPublishCompletedLoRA": "AI-Toolkit: Publish Completed LoRA",
}
