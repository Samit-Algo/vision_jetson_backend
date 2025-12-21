"""
Detections utilities
--------------------

Helpers to extract YOLO detections into simple Python lists.
"""
from typing import List, Tuple


def extract_detections_from_result(result) -> Tuple[List[List[float]], List[str], List[float]]:
    """
    Convert a single YOLO result into (boxes, classes, scores).
    - boxes: list of [x1, y1, x2, y2]
    - classes: list of class names
    - scores: list of confidences
    """
    boxes: List[List[float]] = []
    classes: List[str] = []
    scores: List[float] = []
    if result is None:
        return boxes, classes, scores
    class_names_by_id = result.names if hasattr(result, "names") else {}
    if hasattr(result, "boxes"):
        try:
            xyxy = result.boxes.xyxy.tolist() if hasattr(result.boxes, "xyxy") else []
            cls_list = result.boxes.cls.tolist() if hasattr(result.boxes, "cls") else []
            conf_list = result.boxes.conf.tolist() if hasattr(result.boxes, "conf") else []
            for detection_index, box in enumerate(xyxy):
                boxes.append([float(box[0]), float(box[1]), float(box[2]), float(box[3])])
                class_id = int(cls_list[detection_index]) if detection_index < len(cls_list) else -1
                classes.append(class_names_by_id.get(class_id, str(class_id)))
                score = float(conf_list[detection_index]) if detection_index < len(conf_list) else 0.0
                scores.append(score)
        except Exception:  # noqa: BLE001
            pass
    return boxes, classes, scores


