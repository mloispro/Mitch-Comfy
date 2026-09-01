from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


SECONDARY_IDENTITY_MAX = 0.42
SECONDARY_TO_MAIN_MAX = 0.50
SECONDARY_DUPLICATE_MAX = 0.72


def _normalized(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    return value / max(float(np.linalg.norm(value)), 1e-8)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(_normalized(left), _normalized(right)))


@dataclass(frozen=True)
class IdentityScopeReport:
    status: str
    detected_face_count: int
    main_face_index: int | None
    main_selection_method: str
    main_identity_similarity: float
    main_detection_confidence: float
    maximum_secondary_identity_similarity: float
    maximum_secondary_to_main_similarity: float
    maximum_secondary_pair_similarity: float
    secondary_identity_limit: float
    secondary_to_main_limit: float
    secondary_duplicate_limit: float
    faces: list[dict]
    failures: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate_identity_scope(
    face_embeddings: Sequence[np.ndarray],
    face_bboxes: Sequence[Sequence[float]],
    face_confidences: Sequence[float],
    identity_centroid: np.ndarray,
    main_identity_minimum: float,
    secondary_identity_maximum: float = SECONDARY_IDENTITY_MAX,
    secondary_to_main_maximum: float = SECONDARY_TO_MAIN_MAX,
    secondary_duplicate_maximum: float = SECONDARY_DUPLICATE_MAX,
    preferred_main_index: int | None = None,
) -> IdentityScopeReport:
    """Score one intended main face and reject identity leakage elsewhere.

    Callers that know the subject's scene position should pass ``preferred_main_index``.
    Falling back to the most identity-similar face is retained for callers without
    scene-role information.
    """
    if not face_embeddings:
        return IdentityScopeReport(
            status="rejected",
            detected_face_count=0,
            main_face_index=None,
            main_selection_method="none",
            main_identity_similarity=-1.0,
            main_detection_confidence=0.0,
            maximum_secondary_identity_similarity=-1.0,
            maximum_secondary_to_main_similarity=-1.0,
            maximum_secondary_pair_similarity=-1.0,
            secondary_identity_limit=secondary_identity_maximum,
            secondary_to_main_limit=secondary_to_main_maximum,
            secondary_duplicate_limit=secondary_duplicate_maximum,
            faces=[],
            failures=["no_detected_face"],
        )

    embeddings = [_normalized(item) for item in face_embeddings]
    identity = _normalized(identity_centroid)
    similarities = [_cosine(identity, embedding) for embedding in embeddings]
    if preferred_main_index is None:
        main_index = int(np.argmax(np.asarray(similarities)))
        main_selection_method = "highest_identity_similarity"
    else:
        main_index = int(preferred_main_index)
        if main_index < 0 or main_index >= len(embeddings):
            raise ValueError(
                f"preferred_main_index {main_index} is outside the detected face range"
            )
        main_selection_method = "caller_provided_scene_role"
    secondary_indexes = [index for index in range(len(embeddings)) if index != main_index]
    secondary_identity = [similarities[index] for index in secondary_indexes]
    secondary_to_main = [
        _cosine(embeddings[main_index], embeddings[index])
        for index in secondary_indexes
    ]
    pairwise_secondary = []
    for offset, left_index in enumerate(secondary_indexes):
        for right_index in secondary_indexes[offset + 1 :]:
            pairwise_secondary.append(
                _cosine(embeddings[left_index], embeddings[right_index])
            )

    max_secondary_identity = max(secondary_identity, default=-1.0)
    max_secondary_to_main = max(secondary_to_main, default=-1.0)
    max_secondary_pair = max(pairwise_secondary, default=-1.0)
    failures = []
    if similarities[main_index] < main_identity_minimum:
        failures.append("main_identity_below_threshold")
    if max_secondary_identity >= secondary_identity_maximum:
        failures.append("identity_leaked_to_secondary_face")
    if max_secondary_to_main >= secondary_to_main_maximum:
        failures.append("secondary_face_too_similar_to_main")
    if max_secondary_pair >= secondary_duplicate_maximum:
        failures.append("duplicate_secondary_faces")

    face_reports = []
    for index, (bbox, confidence, similarity) in enumerate(
        zip(face_bboxes, face_confidences, similarities)
    ):
        face_reports.append(
            {
                "index": index,
                "role": "main" if index == main_index else "secondary",
                "bbox": [round(float(value), 1) for value in bbox],
                "detection_confidence": round(float(confidence), 4),
                "similarity_to_reference_centroid": round(float(similarity), 4),
                "similarity_to_selected_main": round(
                    _cosine(embeddings[main_index], embeddings[index]), 4
                ),
            }
        )
    return IdentityScopeReport(
        status="passed" if not failures else "rejected",
        detected_face_count=len(embeddings),
        main_face_index=main_index,
        main_selection_method=main_selection_method,
        main_identity_similarity=round(float(similarities[main_index]), 4),
        main_detection_confidence=round(float(face_confidences[main_index]), 4),
        maximum_secondary_identity_similarity=round(float(max_secondary_identity), 4),
        maximum_secondary_to_main_similarity=round(float(max_secondary_to_main), 4),
        maximum_secondary_pair_similarity=round(float(max_secondary_pair), 4),
        secondary_identity_limit=secondary_identity_maximum,
        secondary_to_main_limit=secondary_to_main_maximum,
        secondary_duplicate_limit=secondary_duplicate_maximum,
        faces=face_reports,
        failures=failures,
    )
